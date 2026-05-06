---
Title: How can I programmatically access the Anthology's data?
weight: 1
---

The Anthology's data is hosted in our Github repo, which contains all the metadata for all its papers (under /data/xml) and their authors (data/yaml/people.yaml), the volumes those papers are organized into, and the real-world events that presented those volumes. The PDFs are hosted on our servers.

All of this data is accessible via [the ACL Anthology Python module on PyPI](https://pypi.org/project/acl-anthology/), which you can install with pip:

```bash
pip install acl-anthology
```

Please see our [repository documentation]({{<relref "/info/development.md" >}}) or the [Python module documentation](https://acl-anthology.readthedocs.io/) for more information.

You may also be interested in learning [how easy it is to cite our papers]({{< ref "/faq/bib" >}}) in a variety of citation formats.