from __future__ import annotations

import asyncio
import inspect

from dataclasses import dataclass, field
from typing import (
    Any,
    Awaitable,
    Callable,
    Generic,
    Iterator,
    TypeVar,
)


T = TypeVar("T")
U = TypeVar("U")


@dataclass
class Context:
    """
    Execution context shared by all nodes during a single composition run.

    The context is intentionally small. Future extensions may use `data`
    for request-scoped services, metadata, caching, tracing, authorization,
    dataloaders, etc.
    """

    data: dict[str, Any] = field(default_factory=dict)


class Node(Generic[T]):
    """
    Base class for a deferred computation.

    A Node describes a computation but does not execute it immediately.
    Execution happens through resolve(), run_async(), or run().

    Nodes can also expose their statically known child nodes through
    children(), which allows the composition tree to be inspected without
    executing it.
    """

    async def resolve(self, context: Context) -> T:
        raise NotImplementedError

    def children(self) -> tuple[Node[Any], ...]:
        """
        Return statically known child nodes.

        The default implementation represents a leaf node.

        Some nodes, especially BindNode, may create additional nodes only
        during execution. Such dynamically created nodes are therefore not
        visible through static tree inspection before resolution.
        """

        return ()

    def map(
        self,
        fn: Callable[[T], U | Awaitable[U] | Node[U]],
    ) -> Node[U]:
        """
        Transform the result of this node.

        The mapping function may return:
        - a plain value
        - an awaitable
        - another Node
        """

        return MapNode(
            source=self,
            fn=fn,
        )

    def bind(
        self,
        fn: Callable[[T], Node[U]],
    ) -> Node[U]:
        """
        Create a dependent computation.

        The next node is constructed only after this node has been resolved.
        """

        return BindNode(
            source=self,
            fn=fn,
        )


@dataclass
class ValueNode(Node[T]):
    """
    Node containing an already available value.
    """

    value: T

    async def resolve(self, context: Context) -> T:
        return self.value


@dataclass
class DeferredNode(Node[T]):
    """
    Deferred computation.

    The factory is called only when the node is resolved.

    It may return:
    - a plain value
    - an awaitable
    - another Node
    """

    factory: Callable[[], T | Awaitable[T] | Node[T]]

    async def resolve(self, context: Context) -> T:
        value = self.factory()
        return await resolve_value(value, context)

@dataclass
class ContextDeferredNode(Node[T]):
    """
    Deferred computation with access to the current execution Context.

    The factory is called only when the node is resolved and receives
    the Context associated with the current run.

    It may return:
    - a plain value
    - an awaitable
    - another Node
    """

    factory: Callable[
        [Context],
        T | Awaitable[T] | Node[T],
    ]

    async def resolve(
        self,
        context: Context,
    ) -> T:
        value = self.factory(context)

        return await resolve_value(
            value,
            context,
        )

@dataclass
class MapNode(Node[U], Generic[T, U]):
    """
    Transformation of another node's result.
    """

    source: Node[T]
    fn: Callable[[T], U | Awaitable[U] | Node[U]]

    def children(self) -> tuple[Node[Any], ...]:
        return (self.source,)

    async def resolve(self, context: Context) -> U:
        value = await self.source.resolve(context)
        mapped = self.fn(value)

        return await resolve_value(
            mapped,
            context,
        )


@dataclass
class BindNode(Node[U], Generic[T, U]):
    """
    Dependent composition.

    The next node can only be constructed after the source node has
    been resolved.

    Static inspection exposes only the source node. The node created by
    `fn` exists only after the source has been resolved.
    """

    source: Node[T]
    fn: Callable[[T], Node[U]]

    def children(self) -> tuple[Node[Any], ...]:
        return (self.source,)

    async def resolve(self, context: Context) -> U:
        value = await self.source.resolve(context)

        next_node = self.fn(value)

        return await next_node.resolve(context)


@dataclass
class GatherNode(Node[tuple[Any, ...]]):
    """
    Resolve independent nodes concurrently.

    This is the composition equivalent of asyncio.gather().
    """

    nodes: tuple[Node[Any], ...]

    def children(self) -> tuple[Node[Any], ...]:
        return self.nodes

    async def resolve(
        self,
        context: Context,
    ) -> tuple[Any, ...]:

        result = await asyncio.gather(
            *(
                node.resolve(context)
                for node in self.nodes
            )
        )

        return tuple(result)


async def resolve_value(
    value: Any,
    context: Context,
) -> Any:
    """
    Resolve a value until an ordinary Python value is produced.

    Supported chains include:

        Node -> value
        Node -> awaitable -> value
        awaitable -> Node -> value
        Node -> Node -> awaitable -> value

    Collections are intentionally NOT flattened here.

    A list, tuple, dict, etc. is considered an ordinary value.
    Domain-specific layers such as HTML may choose to interpret or flatten
    collections themselves.
    """

    while True:

        if isinstance(value, Node):
            value = await value.resolve(context)
            continue

        if inspect.isawaitable(value):
            value = await value
            continue

        return value


def value(value: T) -> Node[T]:
    """
    Wrap an already available value into a Node.
    """

    return ValueNode(value)


def defer(
    factory: Callable[
        [],
        T | Awaitable[T] | Node[T],
    ],
) -> Node[T]:
    """
    Create a deferred computation.

    The factory is not executed immediately.

    Example:

        user = defer(
            lambda: user_service.get(user_id)
        )
    """

    return DeferredNode(factory)


def gather(
    *nodes: Node[Any],
) -> Node[tuple[Any, ...]]:
    """
    Resolve several independent nodes concurrently.

    Example:

        result = gather(
            user,
            roles,
            events,
        )
    """

    return GatherNode(nodes)


def component(
    fn: Callable[..., T | Awaitable[T] | Node[T]],
) -> Callable[..., Node[T]]:
    """
    Decorator converting a regular function into a deferred component.

    Both synchronous and asynchronous functions are supported.

    Example:

        @component
        async def load_user(user_id):
            return await api.get_user(user_id)

        node = load_user(123)
    """

    def wrapped(*args, **kwargs) -> Node[T]:
        return defer(
            lambda: fn(*args, **kwargs)
        )

    return wrapped

def component_with_context(
    fn: Callable[..., T | Awaitable[T] | Node[T]],
) -> Callable[..., Node[T]]:
    """
    Decorator converting a function with access to the current execution
    Context into a deferred component.

    The decorated function should accept Context as a keyword-only argument.

    Example:

        @component_with_context
        async def CurrentUser(
            user_service: UserService,
            *,
            context: Context,
        ) -> User:
            user_id = context.data["user_id"]
            return await user_service.get(user_id)

        plan = CurrentUser(user_service)

        result = await run_async(
            plan,
            context=Context(
                data={
                    "user_id": 123,
                }
            ),
        )
    """

    def wrapped(*args, **kwargs) -> Node[T]:

        return ContextDeferredNode(
            factory=lambda context:
                fn(
                    *args,
                    context=context,
                    **kwargs,
                )
        )

    return wrapped
    
def walk(
    node: Node[Any],
) -> Iterator[Node[Any]]:
    """
    Depth-first traversal of the statically known composition tree.

    The node itself is yielded first, followed by its children.

    Example:

        plan = gather(
            value(1),
            value(2).map(str),
        )

        for item in walk(plan):
            print(type(item).__name__)

    Output:

        GatherNode
        ValueNode
        MapNode
        ValueNode

    Note:
        Dynamically created nodes, such as the result of BindNode.fn,
        cannot be inspected before execution and are therefore not included.
    """

    yield node

    for child in node.children():
        yield from walk(child)


def walk_types(
    node: Node[Any],
) -> Iterator[type[Node[Any]]]:
    """
    Convenience iterator returning node types instead of node instances.

    Example:

        list(walk_types(plan))
    """

    for item in walk(node):
        yield type(item)


async def run_async(
    node: Node[T],
    *,
    context: Context | None = None,
) -> T:
    """
    Resolve a composition asynchronously.

    A new Context is created unless one is explicitly supplied.
    """

    execution_context = (
        context
        if context is not None
        else Context()
    )

    return await node.resolve(
        execution_context
    )


def run(
    node: Node[T],
    *,
    context: Context | None = None,
) -> T:
    """
    Resolve a composition from synchronous code.

    This function must not be called from an already running asyncio
    event loop. In asynchronous applications use:

        await run_async(node)
    """

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(
            run_async(
                node,
                context=context,
            )
        )

    raise RuntimeError(
        "functing.run() cannot be called from a running asyncio "
        "event loop. Use 'await functing.run_async(...)' instead."
    )
