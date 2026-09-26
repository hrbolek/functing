```python
"""
Runnable examples for functing.core.Context.

Run from the repository root:

    python core_examples_context.py
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

from functing.core import (
    Context,
    Node,
    component_with_context,
    defer,
    gather,
    run_async,
    value,
)


def headline(title: str) -> None:
    print()
    print("=" * 72)
    print(title)
    print("=" * 72)


# ---------------------------------------------------------------------------
# Demo domain
# ---------------------------------------------------------------------------

@dataclass
class User:
    id: int
    name: str
    organisation_id: int


class UserService:
    async def get(self, user_id: int) -> User:
        print(f"UserService.get({user_id}) started")
        await asyncio.sleep(0.2)

        user = User(
            id=user_id,
            name=f"User {user_id}",
            organisation_id=10,
        )

        print(f"UserService.get({user_id}) finished")
        return user


async def get_roles(user_id: int) -> list[str]:
    print(f"get_roles({user_id}) started")
    await asyncio.sleep(0.3)
    print(f"get_roles({user_id}) finished")

    return [
        "administrator",
        "teacher",
    ]


async def get_events(user_id: int) -> list[str]:
    print(f"get_events({user_id}) started")
    await asyncio.sleep(0.3)
    print(f"get_events({user_id}) finished")

    return [
        "Conference",
        "Exam",
    ]


# ---------------------------------------------------------------------------
# Example 1: custom Node reading directly from Context
# ---------------------------------------------------------------------------

class ContextValue(Node[Any]):
    """
    Minimal example of a custom Node using the execution Context directly.
    """

    def __init__(self, key: str):
        self.key = key

    async def resolve(
        self,
        context: Context,
    ) -> Any:
        return context.data[self.key]


async def example_context_value() -> None:
    headline("1. Reading values from Context")

    context = Context(
        data={
            "message": "Hello from Context",
            "user_id": 123,
        }
    )

    plan = gather(
        ContextValue("message"),
        ContextValue("user_id"),
    )

    result = await run_async(
        plan,
        context=context,
    )

    print(f"result = {result}")


# ---------------------------------------------------------------------------
# Example 2: reuse one plan with different execution contexts
# ---------------------------------------------------------------------------

async def example_context_reuse() -> None:
    headline("2. Reusing one plan with different contexts")

    plan = gather(
        ContextValue("message"),
        ContextValue("user_id"),
    )

    context_a = Context(
        data={
            "message": "Request A",
            "user_id": 100,
        }
    )

    context_b = Context(
        data={
            "message": "Request B",
            "user_id": 200,
        }
    )

    result_a = await run_async(
        plan,
        context=context_a,
    )

    result_b = await run_async(
        plan,
        context=context_b,
    )

    print(f"result_a = {result_a}")
    print(f"result_b = {result_b}")


# ---------------------------------------------------------------------------
# Example 3: component_with_context
# ---------------------------------------------------------------------------

@component_with_context
async def CurrentUser(
    user_service: UserService,
    *,
    context: Context,
) -> User:
    """
    Context supplies execution-specific data.

    UserService is supplied while building the composition plan and may
    therefore be a singleton or another long-lived dependency.
    """

    user_id = context.data["user_id"]

    return await user_service.get(
        user_id
    )


async def example_component_with_context() -> None:
    headline("3. @component_with_context")

    user_service = UserService()

    # The Node is created here.
    # CurrentUser's body has not executed yet.
    plan = CurrentUser(
        user_service
    )

    print(f"plan type = {type(plan).__name__}")
    print("CurrentUser has not executed yet.")

    context = Context(
        data={
            "user_id": 1,
        }
    )

    result = await run_async(
        plan,
        context=context,
    )

    print(f"result = {result}")


# ---------------------------------------------------------------------------
# Example 4: same component plan, different request data
# ---------------------------------------------------------------------------

async def example_component_context_reuse() -> None:
    headline("4. Reusing a context-aware component")

    user_service = UserService()

    plan = CurrentUser(
        user_service
    )

    context_a = Context(
        data={
            "user_id": 1,
        }
    )

    context_b = Context(
        data={
            "user_id": 2,
        }
    )

    user_a = await run_async(
        plan,
        context=context_a,
    )

    user_b = await run_async(
        plan,
        context=context_b,
    )

    print(f"user_a = {user_a}")
    print(f"user_b = {user_b}")


# ---------------------------------------------------------------------------
# Example 5: component_with_context + bind + gather
# ---------------------------------------------------------------------------

async def example_context_composition() -> None:
    headline("5. component_with_context + bind + gather")

    user_service = UserService()

    context = Context(
        data={
            "user_id": 1,
        }
    )

    current_user = CurrentUser(
        user_service
    )

    plan = current_user.bind(
        lambda user:
            gather(
                value(user),

                defer(
                    lambda:
                        get_roles(
                            user.id
                        )
                ),

                defer(
                    lambda:
                        get_events(
                            user.id
                        )
                ),
            )
    )

    loop = asyncio.get_running_loop()
    started = loop.time()

    user, roles, events = await run_async(
        plan,
        context=context,
    )

    elapsed = loop.time() - started

    print(f"user = {user}")
    print(f"roles = {roles}")
    print(f"events = {events}")
    print(f"elapsed = {elapsed:.2f} s")

    print(
        "Expected: CurrentUser first (~0.2 s), then roles and events "
        "in parallel (~0.3 s), total about 0.5 s."
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main_async() -> None:
    print("functing.core Context examples")

    await example_context_value()
    await example_context_reuse()
    await example_component_with_context()
    await example_component_context_reuse()
    await example_context_composition()

    headline("Done")


def main() -> None:
    asyncio.run(
        main_async()
    )


if __name__ == "__main__":
    main()
```
