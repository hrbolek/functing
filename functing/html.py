from __future__ import annotations

import asyncio

from dataclasses import dataclass
from html import escape
from typing import Any

from .core import Context, Node, resolve_value


class Html(str):
    """
    Marker type for already rendered HTML.

    Plain str values are treated as text and escaped.
    Html values are considered already rendered and are not escaped again.
    """

    pass


class HtmlNode(Node[Html]):
    """
    Base class for nodes producing HTML.
    """

    pass


@dataclass
class FragmentNode(HtmlNode):
    """
    Group several children without adding an enclosing HTML element.
    """

    children: tuple[Any, ...]

    async def resolve(
        self,
        context: Context,
    ) -> Html:
        return await render_children(
            self.children,
            context,
        )


@dataclass
class TagNode(HtmlNode):
    """
    HTML element.
    """

    name: str
    children: tuple[Any, ...]
    props: dict[str, Any]

    async def resolve(
        self,
        context: Context,
    ) -> Html:
        attributes = render_props(
            self.props
        )

        content = await render_children(
            self.children,
            context,
        )

        return Html(
            f"<{self.name}{attributes}>"
            f"{content}"
            f"</{self.name}>"
        )


async def render_child(
    child: Any,
    context: Context,
) -> Html:
    """
    Resolve and render one HTML child.

    Rules:

    - None -> empty output
    - Html -> already rendered, no escaping
    - list / tuple -> rendered as sibling children
    - everything else -> converted to str and escaped
    """

    value = await resolve_value(
        child,
        context,
    )

    if value is None:
        return Html("")

    if isinstance(value, Html):
        return value

    if isinstance(value, (list, tuple)):
        return await render_children(
            value,
            context,
        )

    return Html(
        escape(
            str(value)
        )
    )


async def render_children(
    children,
    context: Context,
) -> Html:
    """
    Resolve sibling children concurrently and concatenate their HTML output.
    """

    rendered = await asyncio.gather(
        *(
            render_child(
                child,
                context,
            )
            for child in children
        )
    )

    return Html(
        "".join(rendered)
    )


def render_props(
    props: dict[str, Any],
) -> str:
    """
    Render HTML attributes.

    Conventions:

        class_="card"
            -> class="card"

        data_id="123"
            -> data-id="123"

        disabled=True
            -> disabled

        disabled=False
            -> omitted

        value=None
            -> omitted
    """

    result: list[str] = []

    for key, value in props.items():

        if value is None:
            continue

        # Python-safe attribute names:
        #
        # class_ -> class
        # for_   -> for
        if key.endswith("_"):
            key = key[:-1]

        # data_id -> data-id
        # aria_label -> aria-label
        key = key.replace("_", "-")

        if isinstance(value, bool):
            if value:
                result.append(
                    f" {key}"
                )

            continue

        rendered_value = escape(
            str(value),
            quote=True,
        )

        result.append(
            f' {key}="{rendered_value}"'
        )

    return "".join(result)


def raw(
    value: str,
) -> Html:
    """
    Mark a string as already rendered / trusted HTML.

    Example:

        Div(
            raw("<strong>Hello</strong>")
        )

    Use only with trusted content.
    """

    return Html(value)


def fragment(
    *children: Any,
) -> HtmlNode:
    """
    Group several children without adding an enclosing element.

    Example:

        fragment(
            Span("A"),
            Span("B"),
        )
    """

    return FragmentNode(
        children=children,
    )


def tag(
    name: str,
):
    """
    Create an HTML tag factory.

    Example:

        Div = tag("div")

        node = Div(
            "Hello",
            class_="container",
        )
    """

    def create(
        *children: Any,
        **props: Any,
    ) -> HtmlNode:

        return TagNode(
            name=name,
            children=children,
            props=props,
        )

    return create


# ---------------------------------------------------------------------------
# Common HTML tags
# ---------------------------------------------------------------------------

HtmlTag = tag("html")

Head = tag("head")
Body = tag("body")

Title = tag("title")

Div = tag("div")
Span = tag("span")

P = tag("p")

H1 = tag("h1")
H2 = tag("h2")
H3 = tag("h3")
H4 = tag("h4")
H5 = tag("h5")
H6 = tag("h6")

Ul = tag("ul")
Ol = tag("ol")
Li = tag("li")

Table = tag("table")
Thead = tag("thead")
Tbody = tag("tbody")
Tfoot = tag("tfoot")

Tr = tag("tr")
Th = tag("th")
Td = tag("td")

A = tag("a")

Form = tag("form")
Label = tag("label")
Input = tag("input")
Button = tag("button")

Section = tag("section")
Article = tag("article")
Header = tag("header")
Footer = tag("footer")
Main = tag("main")
Nav = tag("nav")
