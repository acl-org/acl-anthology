# Copyright 2024 Marcel Bollmann <marcel@bollmann.me>
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

"""Functions for generating citation references."""

from __future__ import annotations

import citeproc
from citeproc import (
    Citation,
    CitationItem,
    CitationStylesBibliography,
    CitationStylesStyle,
)
from citeproc.source.json import CiteProcJSON
from pathlib import Path
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from ..collections import Paper
    from ..people import NameSpecification


class CitationStyleDict(dict[str | Path, Any]):
    """Dictionary mapping names of citation styles to their `citeproc.CitationStylesStyle` objects, auto-loading styles on first access."""

    def __getitem__(self, key: str | Path) -> CitationStylesStyle:
        style = dict.get(self, key)
        if style is None:
            if Path(key).is_file():
                # Assume that key is a filename
                filename = key
            else:
                # Assume that key is the name of a style in citeproc-py-styles
                raise ValueError(
                    "Names of citation styles are currently not supported; give the name to a CSL file instead."
                )
            if not Path(filename).is_file():
                raise KeyError(
                    f"Could not resolve '{key}' to a filename of a citation style"
                )
            style = CitationStylesStyle(filename)
            self.__setitem__(key, style)
        return style


citation_styles = CitationStyleDict()
"""Global object for accessing `citeproc.CitationStylesStyle` objects."""


def citeproc_render_html(
    citeproc_dict: dict[str, Any],
    style: str | Path,
    link_title: bool = True,
) -> str:
    """Render a bibliography entry with a given CSL style.

    Arguments:
        citeproc_dict: A dictionary with publication metadata as expected by CiteProcJSON.
        style: A path to a CSL file.
        link_title: If True, wraps the title in a link to the entry's URL.

    Returns:
        The bibliography entry as a single string with HTML markup.

    Note:
        The reason for returning a string is that this is what we get from citeproc-py's `render_bibliography()` function.  If the result was parsed with LXML, we could turn it into a proper [MarkupText][acl_anthology.text.MarkupText] object.  However, since the most common use case of this function requires the HTML-ified string, we do not do this here as it would introduce unnecessary overhead in this case.
    """
    source = CiteProcJSON([citeproc_dict])
    item = CitationItem(citeproc_dict["id"])
    bib = CitationStylesBibliography(
        citation_styles[style], source, citeproc.formatter.html
    )
    bib.register(Citation([item]))
    rendered_list = bib.style.render_bibliography([item])[0]
    if link_title:
        link_text = f'<a href="{citeproc_dict["URL"]}">{citeproc_dict["title"]}</a>'
        rendered_list = [
            str(x) if x != citeproc_dict["title"] else link_text for x in rendered_list
        ]
    return "".join(rendered_list)


def _format_names(names: list[NameSpecification]) -> str:
    match len(names):
        case 0:
            return "N.N."
        case 1:
            return names[0].name.as_first_last()
        case 2:
            return " and ".join(ns.name.as_first_last() for ns in names)
        case _:
            return f"{', '.join(ns.name.as_first_last() for ns in names[:-1])}, and {names[-1].name.as_first_last()}"


def _format_pages(pages: str) -> str:
    return pages.replace("--", "–").replace("-", "–")


def render_acl_citation(paper: Paper) -> str:
    """Render a bibliography entry in ACL style.

    Arguments:
        paper: The paper for which to generate the bibliography entry.

    Returns:
        The bibliography entry as a single string with HTML markup.

    Note:
        This function re-implements (parts of) the ACL citation style in pure Python, making it a much faster alternative to [citeproc_render_html][acl_anthology.utils.citation.citeproc_render_html].
    """
    if paper.authors:
        authors = _format_names(paper.authors)
    else:
        editors = paper.get_editors()
        if not editors:
            # No authors, no editors
            authors = ""
        else:
            authors = _format_names(editors)
            if not paper.is_frontmatter:
                authors = f"{authors} ({'eds.' if len(editors) > 1 else 'ed.'})"
    title = f'<a href="{paper.web_url}">{paper.title.as_text()}</a>'
    if paper.is_frontmatter:
        title = f"<i>{title}</i>"
    parent = []
    if paper.bibtype == "inproceedings":
        parent = [f"In <i>{paper.parent.title.as_text()}</i>"]
        if paper.pages:
            pages = _format_pages(paper.pages)
            parent.append(f", {'pages' if '–' in pages else 'page'} {pages}")
        if paper.address:
            parent.append(f", {paper.address}")
        if paper.publisher:
            parent.append(f". {paper.publisher}")
    elif paper.bibtype == "article":
        parent = [f"<i>{paper.get_journal_title()}</i>"]
        if paper.parent.journal_volume:
            parent.append(f", {paper.parent.journal_volume}")
            if (journal_issue := paper.get_issue()) is not None:
                parent.append(f"({journal_issue})")
            if paper.pages:
                parent.append(f":{_format_pages(paper.pages)}")
        elif paper.pages:
            parent.append(f", {_format_pages(paper.pages)}")
    else:
        if paper.publisher:
            parent.append(paper.publisher)
            if paper.address:
                parent.append(f", {paper.address}")

    if authors:
        citation = f"{authors}. {paper.year}. {title}."
    else:
        citation = f"{title}. {paper.year}."

    if parent:
        citation = f"{citation} {''.join(parent)}."

    return citation
