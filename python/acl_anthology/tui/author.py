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

from __future__ import annotations

from dawg import CompletionDAWG  # type: ignore
import itertools as it
from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Input, Label, ListItem, ListView
from typing import Iterator, Optional, TYPE_CHECKING

from ..people import NameLink

if TYPE_CHECKING:
    from ..people import PersonIndex, Person, Name


class PIDSearch:
    def __init__(self, index: PersonIndex) -> None:
        self.index = index
        self.full_dawg = CompletionDAWG(self._yield_full_keys())
        self.cont_dawg = CompletionDAWG(self._yield_cont_keys())

    def _yield_full_keys(self) -> Iterator[str]:
        for pid in self.index:
            if pid.startswith("unverified/"):
                yield f"{pid[len("unverified/"):]}*"
            else:
                yield pid

    def _yield_cont_keys(self) -> Iterator[str]:
        for pid in self.index:
            if pid.startswith("unverified/"):
                mark, j = "*", len("unverified/")
            else:
                mark, j = "", 0
            s = 0
            while (i := pid.find("-", s)) > 0:
                yield f"{pid[i+1:]}{mark}|{pid[j:i+1]}"
                s = i + 1

    def keys(self, prefix: str) -> Iterator[str]:
        if not prefix:
            yield from self.full_dawg.keys()
        elif prefix[0] == "-":
            prefix = prefix[1:]
        else:
            yield from self.full_dawg.keys(prefix)
        if prefix:
            for key in self.cont_dawg.keys(prefix):
                yield "".join(key.split("|")[::-1])


class AuthorList(ListView):
    ids_to_show: reactive[list[str]] = reactive(list, recompose=True)
    append_message: reactive[str] = reactive("")

    BINDINGS = [
        Binding("up", "move_up", "Move up to Author Input", show=False),
    ]

    class MoveUp(Message):
        pass

    class HighlightedEntry(Message):
        def __init__(self, pid: str) -> None:
            self.pid = pid
            super().__init__()

    def compose(self) -> ComposeResult:
        for id_ in self.ids_to_show:
            yield ListItem(
                Label(id_.replace("*", "[dim] (unverified)[/]")),
                name=id_,
            )
        if self.append_message:
            yield ListItem(
                Label(self.append_message),
                disabled=True,
                classes="disabled",
            )

    def action_move_up(self) -> None:
        if self.index == 0:
            self.post_message(self.MoveUp())
        else:
            self.action_cursor_up()

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        if not event.item or not event.item.name:
            return
        if event.item.name[-1] == "*":
            pid = f"unverified/{event.item.name[:-1]}"
        else:
            pid = event.item.name
        self.post_message(self.HighlightedEntry(pid))


class AuthorMetadata(Container):
    person: reactive[Optional[Person]] = reactive(None, recompose=True)

    def compose(self) -> ComposeResult:
        if self.person is None:
            return

        def render_name(name: Name, link_type: NameLink) -> str:
            if link_type == NameLink.INFERRED:
                extra = " [dim](inferred)[/]"
            else:
                extra = ""
            return f"{name.first} [bold]{name.last}[/]{extra}"

        person = self.person
        content = (
            Label(f"{person.id}", name="person-id"),
            Label(""),
            *[Label(f"· {render_name(*entry)}") for entry in person._names],
        )
        yield Container(*content)


class AuthorTab(Container):
    BINDINGS = [
        Binding("down", "move_down", "Move down from Author Input", show=False),
    ]

    max_to_show: int = 40
    search: Optional[PIDSearch] = None
    index: Optional[PersonIndex] = None

    def set_index(self, index: PersonIndex) -> None:
        self.index = index
        self.search = PIDSearch(index)
        self.filter_author_list(Input.Changed(self.query_one("#author-input", Input), ""))

    def compose(self) -> ComposeResult:
        with Vertical(id="author-sidebar"):
            yield Input(
                placeholder="Search for person IDs...",
                restrict="^[a-z0-9-]*$",
                id="author-input",
            )
            yield AuthorList(id="list-view")
        with Vertical(id="author-info"):
            yield AuthorMetadata(id="author-metadata")

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

    def on_author_list_highlighted_entry(
        self, message: AuthorList.HighlightedEntry
    ) -> None:
        if self.index is None:
            return
        person = self.index[message.pid]
        self.query_one("#author-metadata", AuthorMetadata).person = person

    @on(Input.Changed, "#author-input")
    def filter_author_list(self, event: Input.Changed) -> None:
        author_list = self.query_one("#list-view", AuthorList)
        if self.search is None:
            author_list.ids_to_show = []
            author_list.append_message = "SEARCH NOT INITIALIZED"
        else:
            keys = self.search.keys(event.value)
            author_list.ids_to_show = list(it.islice(keys, self.max_to_show))
            if not author_list.ids_to_show:
                author_list.append_message = "No results found"
                return
            try:
                next(keys)
                author_list.append_message = "...more not shown..."
            except StopIteration:
                author_list.append_message = ""
