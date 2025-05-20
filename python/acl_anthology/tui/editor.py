"""
TODO
"""

from __future__ import annotations

from textual import work
from textual.app import App, ComposeResult
from textual.containers import Container, VerticalScroll
from textual.reactive import reactive, var
from textual.widgets import Label, ListItem, ListView, Footer, Header, Static

from ..anthology import Anthology
from ..config import config


class AnthologyEditor(App):
    """ACL Anthology editing app."""

    CSS_PATH = "editor.tcss"
    TITLE = "ACL Anthology Editor"
    BINDINGS = [
        ("q", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        """Compose our UI."""
        yield Header(icon="🕮")
        with Container():
            yield ListView(ListItem(Label("none")), id="list-view")
            with VerticalScroll(id="code-view"):
                yield Static(id="code", expand=True)
        yield Footer()

    def on_mount(self) -> None:
        self.query_one(Container).loading = True
        self.load_anthology()

    @work(thread=True)
    async def load_anthology(self) -> None:
        self.anthology = Anthology(datadir="../data", verbose=False)  # TODO
        self.anthology.load_all()
        self.query_one(Container).loading = False


def main():
    AnthologyEditor().run()


if __name__ == "__main__":
    main()
