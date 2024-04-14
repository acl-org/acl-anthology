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

import citeproc
from citeproc import Citation, CitationItem, CitationStylesBibliography, CitationStylesStyle
from citeproc.source.json import CiteProcJSON
from citeproc_styles import get_style_filepath
from pathlib import Path
import sys
from typing import Any, Optional


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
                filename = get_style_filepath(key)
            if not Path(filename).is_file():
                raise KeyError(f"Could not resolve '{key}' to a filename of a citation style")
            style = CitationStylesStyle(filename)
            self.__setitem__(key, style)
        return style


citation_styles = CitationStyleDict()
"""Global object for accessing `citeproc.CitationStylesStyle` objects."""


def citeproc_render_html(citeproc_dict: dict[str, Any], style: Optional[str | Path] = None, link_title: bool = True) -> str:
    """Render a bibliography entry with a given CSL style.

    Arguments:
        citeproc_dict: A dictionary with publication metadata as expected by CiteProcJSON.
        style: Any citation style supported by [`citeproc-py-styles`](https://github.com/inveniosoftware/citeproc-py-styles) or a path to a CSL file.  If None (default), uses the built-in ACL citation style.
        link_title: If True, wraps the title in a link to the entry's URL.

    Returns:
        The bibliography entry as a single string with HTML markup.

    Note:
        The reason for returning a string is that this is what we get from citeproc-py's `render_bibliography()` function.  If the result was parsed with LXML, we could turn it into a proper [MarkupText][acl_anthology.text.MarkupText] object.  However, since the most common use case of this function requires the HTML-ified string, we do not do this here as it would introduce unnecessary overhead in this case.
    """
    if style is None:
        style = Path(sys.modules["acl_anthology"].__path__[0]) / "data" / "acl.csl"

    source = CiteProcJSON([citeproc_dict])
    item = CitationItem(citeproc_dict["id"])
    bib = CitationStylesBibliography(citation_styles[style], source, citeproc.formatter.html)
    bib.register(Citation([item]))
    rendered_list = bib.style.render_bibliography([item])[0]
    if link_title:
        link_text = f'<a href="{citeproc_dict["URL"]}">{citeproc_dict["title"]}</a>'
        rendered_list = [
            str(x) if x != citeproc_dict["title"] else link_text
            for x in rendered_list
        ]
    return "".join(rendered_list)
