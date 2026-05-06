---
Title: How do I cite papers in the ACL Anthology?
category: citing
weight: 1
---
Citing papers in the ACL Anthology is simple. We provide
- bulk bibliographic exports
- click-to-copy citation keys on each paper page
- per-paper citation downloads

Our primary supported format is BibTeX. The simplest way to cite papers is download the bulk BibTeX exports, and then use the citation keys, which are often inferrable from the paper's author list and title: `{authors}-{year}-{title-word}`, where

- `{authors}` is the last names of the first one or two authors, separated by hyphens; if more than two authors, `etal` is used for the second author
- `{year}` is the four-digit year of publication
- `{title-word}` is the first significant word of the paper's title; additional words are added if needed to create a unique bibkey

Some examples are [galley-etal-2004-whats](https://aclanthology.org/N04-1035/) and [huang-chiang-2005-better](https://aclanthology.org/W05-1506/). For convenience, a button on each paper page provides click-to-copy access to the bibkey.

Bulk downloads for consolidated BibTeX files are available in the following variations.

* _Overleaf-friendly_: [anthology-1.bib](https://aclanthology.org/anthology-1.bib), [anthology-2.bib](https://aclanthology.org/anthology-2.bib) etc. are sharded variants that are under 50 MB each, suitable for direct import into Overleaf repositories.
* _Full, with abstracts_: [anthology+abstracts.bib.gz](https://aclanthology.org/anthology.bib) contains citations for all papers that exist in the Anthology, including abstracts.
* _No abstracts_: [anthology.bib.gz](https://aclanthology.org/anthology.bib.gz) contains all citations but removes abstracts, to save on space.
* _No abstracts, uncompressed_: [anthology.bib](https://aclanthology.org/anthology.bib) is the same as the above, but provided uncompressed, for convenience.

For individual papers, buttons are provided to download citation data in a number of formats, including BibTeX, [MODS XML](https://www.loc.gov/standards/mods/), Endnote, and an informal citation string.
These formats can be downloaded as files or copied to the clipboard via convenient buttons.

Finally, we also offer [an XML paper feed](https://aclanthology.org/papers/index.xml), which is useful in tools like [Zotero](https://www.zotero.org/) and [Mendeley](https://www.mendeley.com/).
