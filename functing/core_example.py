"""
Runnable examples for functing.core.

Run from the repository root:

    python core_examples.py
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from functing.core import (
    Context,
    component,
    defer,
    gather,
    run,
    run_async,
    value,
)


def headline(title: str) -> None:
    print()
    print("=" * 72)
    print(title)
    print("=" * 72)


def example_value() -> None:
    headline("1. value()")
    node = value(42)
    result = run(node)
    print(f"result = {result}")


def example_defer_sync() -> None:
    headline("2. defer() with synchronous function")

    def compute() -> int:
        print("compute() executed")
        return 10 + 20

    node = defer(compute)
    print("Node created. Function has not been executed yet.")

    result = run(node)
    print(f"result = {result}")


def example_map() -> None:
    headline("3. map()")

    node = (
        value(10)
        .map(lambda x: x * 2)
        .map(lambda x: x + 1)
        .map(str)
    )

    result = run(node)
    print(f"result = {result!r}")


@component
def greeting(name: str) -> str:
    print(f"greeting({name!r}) executed")
    return f"Hello {name}"


def example_component() -> None:
    headline("4. @component")

    node = greeting("John")
    print("Component called, but its body has not executed yet.")

    result = run(node)
    print(f"result = {result}")


async def load_number(number: int, delay: float = 0.2) -> int:
    print(f"load_number({number}) started")
    await asyncio.sleep(delay)
    print(f"load_number({number}) finished")
    return number


async def example_defer_async() -> None:
    headline("5. defer() with asynchronous function")

    node = defer(lambda: load_number(42))

    result = await run_async(node)
    print(f"result = {result}")


async def example_gather() -> None:
    headline("6. gather() - concurrent independent computations")

    first = defer(lambda: load_number(1, 0.5))
    second = defer(lambda: load_number(2, 0.5))
    third = defer(lambda: load_number(3, 0.5))

    plan = gather(first, second, third)

    loop = asyncio.get_running_loop()
    started = loop.time()

    result = await run_async(plan)

    elapsed = loop.time() - started

    print(f"result = {result}")
    print(f"elapsed = {elapsed:.2f} s")
    print("Expected: approximately 0.5 s, not 1.5 s.")


@dataclass
class User:
    id: int
    name: str
    organisation_id: int


@dataclass
class Organisation:
    id: int
    name: str


async def get_user(user_id: int) -> User:
    print(f"get_user({user_id}) started")
    await asyncio.sleep(0.2)

    user = User(
        id=user_id,
        name="Alice",
        organisation_id=10,
    )

    print(f"get_user({user_id}) finished")
    return user


async def get_organisation(organisation_id: int) -> Organisation:
    print(f"get_organisation({organisation_id}) started")
    await asyncio.sleep(0.2)

    organisation = Organisation(
        id=organisation_id,
        name="Example University",
    )

    print(f"get_organisation({organisation_id}) finished")
    return organisation


async def example_bind() -> None:
    headline("7. bind() - dependent computation")

    user = defer(lambda: get_user(1))

    organisation = user.bind(
        lambda current_user:
            defer(
                lambda: get_organisation(
                    current_user.organisation_id
                )
            )
    )

    result = await run_async(organisation)
    print(f"result = {result}")


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


async def example_data_composition() -> None:
    headline("8. service-level data composition")

    user = defer(lambda: get_user(1))

    overview = user.bind(
        lambda current_user:
            gather(
                value(current_user),

                defer(
                    lambda: get_roles(
                        current_user.id
                    )
                ),

                defer(
                    lambda: get_events(
                        current_user.id
                    )
                ),

                defer(
                    lambda: get_organisation(
                        current_user.organisation_id
                    )
                ),
            )
    )

    result = await run_async(overview)

    current_user, roles, events, organisation = result

    response = {
        "user": current_user,
        "roles": roles,
        "events": events,
        "organisation": organisation,
    }

    print("composed response:")
    for key, item in response.items():
        print(f"  {key}: {item}")


async def example_context() -> None:
    headline("9. Context")

    context = Context(
        data={
            "message": "Hello from Context",
        }
    )

    node = defer(
        lambda: context.data["message"]
    )

    result = await run_async(
        node,
        context=context,
    )

    print(f"result = {result}")


async def async_examples() -> None:
    await example_defer_async()
    await example_gather()
    await example_bind()
    await example_data_composition()
    await example_context()


def main() -> None:
    print("functing.core examples")

    example_value()
    example_defer_sync()
    example_map()
    example_component()

    asyncio.run(async_examples())

    headline("Done")


if __name__ == "__main__":
    main()
