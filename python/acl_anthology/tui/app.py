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

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.widgets import Footer, Header

from ..anthology import Anthology
from ..config import config

from .author import AuthorTab


class AnthologyApp(App[None]):
    """ACL Anthology textual app."""

    CSS_PATH = "editor.tcss"
    TITLE = "ACL Anthology App"
    BINDINGS = [
        Binding("down", "move_down", "Move down from Author Input", show=False),
        ("q", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        """Compose our UI."""
        yield Header(icon="🕮")
        yield AuthorTab(id="author-tab")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one(Container).loading = True
        self.load_anthology()

    @work(thread=True)
    async def load_anthology(self) -> None:
        self.anthology = Anthology(datadir="../data-new", verbose=False)  # TODO
        config["disable_gc"] = False  # This appears to cause lags later
        self.anthology.load_all()
        self.query_one("#author-tab", AuthorTab).set_index(self.anthology.people)
        self.query_one(Container).loading = False


def main() -> None:
    AnthologyApp().run()


if __name__ == "__main__":
    main()
