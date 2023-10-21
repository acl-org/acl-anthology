# Overview

## What is this?

This is a Python library for accessing data from the [ACL
Anthology](https://aclanthology.org/).

The ACL Anthology is a prime resource for research papers within computational
linguistics and natural language processing.  Metadata for all of its
publications is stored in a [public Github
repository](https://github.com/acl-org/acl-anthology).  This package provides
functionality to access all of the metadata you can find on the website easily
from within Python.  If you are interested in contributing to the Anthology, you
can even use this library to programmatically make changes to the metadata.

## How to use

This package requires **Python 3.10 or newer**. Install via pip:

```bash
pip install acl-anthology-py
```

Instantiate the library, automatically fetching data files from the [ACL
Anthology repo](https://github.com/acl-org/acl-anthology) (requires Git to be
installed on your system):

```python
from acl_anthology import Anthology
anthology = Anthology.from_repo()
```

### Some brief examples

```pycon
>>> paper = anthology.get("C92-1025")
>>> str(paper.title)
Two-Level Morphology with Composition
>>> [author.name for author in paper.authors]
[
    Name(first='Lauri', last='Karttunen'),
    Name(first='Ronald M.', last='Kaplan'),
    Name(first='Annie', last='Zaenen')
]
>>> anthology.find_people("Karttunen, Lauri")
[
    Person(
        id='lauri-karttunen', names=[Name(first='Lauri', last='Karttunen')],
        item_ids=<set of 30 AnthologyIDTuple objects>, comment=None
    )
]
```

### Further information

Look at the [Getting Started guide](guide/getting-started.md) for further
information, or the [API documentation](api/index.md) for detailed descriptions
of the provided functions.
