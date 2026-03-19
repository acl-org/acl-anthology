---
Title: How can I access data from the Anthology?
weight: 1
---

In addition to its papers, the Anthology publishes extensive bibliographic content in a number of formats. We also maintain a Python library that provides clean programmatic access to the Anthology's metadata and content.

### Bibliographic data

Bibliographic data is available for individual papers and in bulk.

For individual papers, buttons are provided to download citation data in a number of formats, including BibTeX, [MODS XML](https://www.loc.gov/standards/mods/), Endnote, and an informal citation string.
These formats can be downloaded as files or copied to the clipboard via convenient buttons.

For bulk downloads, we provide consolidated BibTeX files in the following variations:

* [anthology+abstracts.bib.gz](https://aclanthology.org/anthology.bib) contains citations for all papers that exist in the Anthology, including abstracts.
* [anthology.bib.gz](https://aclanthology.org/anthology.bib.gz) contains all citations but removes abstracts, to save on space.
* [anthology.bib](https://aclanthology.org/anthology.bib) is the same as the above, but provided uncompressed, for convenience.
* [anthology-1.bib](https://aclanthology.org/anthology-1.bib), [anthology-2.bib](https://aclanthology.org/anthology-2.bib) etc. are sharded variants that are under 50 MB each, suitable for direct import into Overleaf repositories.

Finally, we also offer [an XML paper feed](https://aclanthology.org/papers/index.xml), which is useful in tools like [Zotero](https://www.zotero.org/) and [Mendeley](https://www.mendeley.com/).

### Python library

The Anthology also provides a Python library, [`acl-anthology`](https://pypi.org/project/acl-anthology/), which is the preferred way to access the content inside the Anthology programmatically. This library can be easily installed via pip:

```bash
pip install acl-anthology
```

Documentation on the API can be found at [readthedocs](https://acl-anthology.readthedocs.io/), and its source code in our [GitHub repository](https://github.com/acl-org/acl-anthology/tree/master/python).
