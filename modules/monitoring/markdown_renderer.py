"""Render safe Markdown for AI monitor responses."""

from markdown_it import MarkdownIt


_renderer = (
    MarkdownIt("commonmark", {"breaks": True, "html": False, "linkify": False})
    .enable("table")
    .enable("strikethrough")
)


def render_markdown(source: str) -> str:
    return _renderer.render(source)
