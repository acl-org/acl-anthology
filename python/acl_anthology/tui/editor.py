# Copyright 2025 Marcel Bollmann <marcel@bollmann.me>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
TODO
"""

from __future__ import annotations

from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical, VerticalScroll
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Input, Label, ListItem, ListView, Footer, Header, Static

from ..anthology import Anthology

# from ..config import config


class AuthorList(ListView):
    ids_to_show: reactive[list[str]] = reactive(list, recompose=True)
    max_to_show: int = 250

    BINDINGS = [
        Binding("up", "move_up", "Move up to Author Input", show=False),
    ]

    class MoveUp(Message):
        pass

    def compose(self) -> ComposeResult:
        for id_ in self.ids_to_show[: self.max_to_show]:
            yield ListItem(Label(id_))
        if (diff := len(self.ids_to_show) - self.max_to_show) > 0:
            yield ListItem(
                Label(f"...{diff} more not shown..."),
                disabled=True,
                classes="more-not-shown",
            )

    def action_move_up(self) -> None:
        if self.index == 0:
            self.post_message(self.MoveUp())
        else:
            self.action_cursor_up()


class AnthologyEditor(App[None]):
    """ACL Anthology editing app."""

    CSS_PATH = "editor.tcss"
    TITLE = "ACL Anthology"
    SUB_TITLE = "Author Editor"
    BINDINGS = [
        Binding("down", "move_down", "Move down from Author Input", show=False),
        ("q", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        """Compose our UI."""
        yield Header(icon="🕮")
        with Container():
            with Vertical(id="author-sidebar"):
                yield Input(
                    placeholder="Type an author ID",
                    restrict="^[a-z0-9-]*$",
                    id="author-input",
                )
                yield AuthorList(id="list-view")
            with VerticalScroll(id="code-view"):
                yield Static(id="code", expand=True)
        yield Footer()

    def action_move_down(self) -> None:
        if self.query_one("#author-input").has_focus:
            lv = self.query_one("#list-view", AuthorList)
            if lv.ids_to_show:
                lv.index = 0
                lv.focus()

    def on_author_list_move_up(self) -> None:
        lv = self.query_one("#list-view", AuthorList)
        if lv.has_focus and lv.index == 0:
            self.query_one("#author-input").focus()

    @on(Input.Changed, "#author-input")
    def filter_author_list(self, event: Input.Changed) -> None:
        author_list = self.query_one("#list-view", AuthorList)
        if not event.value:
            author_list.ids_to_show = self.pids
        else:
            author_list.ids_to_show = [
                pid for pid in self.pids if pid.startswith(event.value)
            ]

    def on_mount(self) -> None:
        self.query_one(Container).loading = True
        self.load_anthology()

    @work(thread=True)
    async def load_anthology(self) -> None:
        self.anthology = Anthology(datadir="../data", verbose=False)  # TODO
        self.anthology.load_all()
        self.pids = sorted(self.anthology.people.keys())
        self.query_one("#list-view", AuthorList).ids_to_show = self.pids
        self.query_one(Container).loading = False


def main() -> None:
    AnthologyEditor().run()


if __name__ == "__main__":
    main()
