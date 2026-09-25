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
    return ["administrator", "teacher"]


async def get_events(user_id: int) -> list[str]:
    print(f"get_events({user_id}) started")
    await asyncio.sleep(0.3)
    print(f"get_events({user_id}) finished")
    return ["Conference", "Exam"]


class ContextValue(Node[Any]):
    """Read a value from the current execution Context."""

    def __init__(self, key: str):
        self.key = key

    async def resolve(self, context: Context) -> Any:
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

    result = await run_async(plan, context=context)
    print(f"result = {result}")


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

    result_a = await run_async(plan, context=context_a)
    result_b = await run_async(plan, context=context_b)

    print(f"result_a = {result_a}")
    print(f"result_b = {result_b}")


class CurrentUser(Node[User]):
    """Load the current user from execution-scoped data and services."""

    async def resolve(self, context: Context) -> User:
        user_id = context.data["user_id"]
        service: UserService = context.data["user_service"]
        return await service.get(user_id)


async def example_context_service() -> None:
    headline("3. Request-scoped service in Context")

    context = Context(
        data={
            "user_id": 1,
            "user_service": UserService(),
        }
    )

    result = await run_async(
        CurrentUser(),
        context=context,
    )

    print(f"result = {result}")


async def example_context_composition() -> None:
    headline("4. Context + bind + gather")

    context = Context(
        data={
            "user_id": 1,
            "user_service": UserService(),
        }
    )

    current_user = CurrentUser()

    plan = current_user.bind(
        lambda user:
            gather(
                value(user),
                defer(lambda: get_roles(user.id)),
                defer(lambda: get_events(user.id)),
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
        "Expected: user load (~0.2 s), then roles and events in parallel "
        "(~0.3 s), total about 0.5 s."
    )


async def main_async() -> None:
    print("functing.core Context examples")

    await example_context_value()
    await example_context_reuse()
    await example_context_service()
    await example_context_composition()

    headline("Done")


def main() -> None:
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
