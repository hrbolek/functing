"""
Runnable demo for functing.html.

Run from the repository root:

    python html_example.py

Expected package layout:

    functing/
        core.py
        html.py
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from functing.core import component, run, run_async
from functing.html import (
    A,
    Body,
    Button,
    Div,
    H1,
    H2,
    Head,
    HtmlTag,
    Li,
    Main,
    P,
    Span,
    Title,
    Ul,
    fragment,
    raw,
)


# ---------------------------------------------------------------------------
# Demo data
# ---------------------------------------------------------------------------

@dataclass
class User:
    id: int
    name: str
    role: str
    active: bool


USERS = {
    1: User(1, "Alice", "Administrator", True),
    2: User(2, "Bob", "Teacher", True),
    3: User(3, "Charlie <script>alert('x')</script>", "Student", False),
}


async def load_user(user_id: int) -> User:
    """
    Simulate an asynchronous service/API call.
    """
    print(f"load_user({user_id}) started")

    await asyncio.sleep(0.5)

    print(f"load_user({user_id}) finished")

    return USERS[user_id]


# ---------------------------------------------------------------------------
# Reusable components
# ---------------------------------------------------------------------------

@component
def Badge(text: str, active: bool = True):
    return Span(
        text,
        class_="badge",
        data_active=active,
    )


@component
def UserCard(user: User):
    return Div(
        H2(user.name),
        P(
            "Role: ",
            Span(user.role, class_="role"),
        ),
        Badge(
            "Active" if user.active else "Inactive",
            active=user.active,
        ),
        class_="user-card",
        data_user_id=user.id,
    )


@component
async def AsyncUserCard(user_id: int):
    """
    Async component.

    When several AsyncUserCard instances are siblings,
    html.render_children() resolves them concurrently.
    """
    user = await load_user(user_id)

    return UserCard(user)


@component
def Navigation():
    return Ul(
        Li(A("Home", href="/")),
        Li(A("Users", href="/users")),
        Li(A("About", href="/about")),
        class_="navigation",
    )


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

def create_page():
    return HtmlTag(
        Head(
            Title("Functing HTML demo"),
        ),
        Body(
            Main(
                H1("Functing HTML demo"),

                P(
                    "This page is composed from synchronous and "
                    "asynchronous Python components."
                ),

                Navigation(),

                H2("Escaping"),

                P(
                    "Plain strings are escaped: ",
                    "<strong>This is text, not HTML.</strong>",
                ),

                P(
                    "Trusted raw HTML: ",
                    raw("<strong>This is rendered as HTML.</strong>"),
                ),

                H2("Fragments"),

                Div(
                    fragment(
                        Span("A"),
                        " + ",
                        Span("B"),
                    ),
                    class_="fragment-example",
                ),

                H2("Async users"),

                Div(
                    AsyncUserCard(1),
                    AsyncUserCard(2),
                    AsyncUserCard(3),
                    class_="users",
                ),

                Button(
                    "Example button",
                    type="button",
                    disabled=False,
                    data_demo="true",
                ),

                class_="container",
            )
        )
    )


# ---------------------------------------------------------------------------
# Sync demo
# ---------------------------------------------------------------------------

def sync_demo() -> None:
    print()
    print("=" * 72)
    print("SYNC RENDER")
    print("=" * 72)

    page = Div(
        H1("Synchronous example"),
        P("Rendered through functing.core.run()."),
        UserCard(USERS[1]),
    )

    html = run(page)

    print(html)


# ---------------------------------------------------------------------------
# Async demo
# ---------------------------------------------------------------------------

async def async_demo() -> None:
    print()
    print("=" * 72)
    print("ASYNC RENDER")
    print("=" * 72)

    page = create_page()

    loop = asyncio.get_running_loop()
    started = loop.time()

    html = await run_async(page)

    elapsed = loop.time() - started

    print()
    print(html)

    print()
    print(f"Render time: {elapsed:.2f} s")
    print(
        "Three user loads each wait 0.5 s, so concurrent rendering "
        "should take about 0.5 s rather than 1.5 s."
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("functing.html demo")

    sync_demo()

    asyncio.run(
        async_demo()
    )


if __name__ == "__main__":
    main()
