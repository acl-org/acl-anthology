# Getting Started

To use this library, you need **Python 3.10 or newer**.  For automatically
fetching data from the main ACL Anthology repository, you will also need to have
**Git** installed.

## Installation

The library is available as a [PyPI
package](https://pypi.org/project/acl-anthology-py/) and can therefore simply be
installed via pip:

```bash
pip install acl-anthology-py
```

Alternatively, you can [download releases from
Github](https://github.com/mbollmann/acl-anthology-py/releases/).

## Instantiating the Anthology

### From the official repository

The easiest way to instantiate the Anthology in Python is as follows:

```python
from acl_anthology import Anthology

# Instantiate the Anthology from the official repository
anthology = Anthology.from_repo()
```

This will automatically fetch the latest metadata from the [official ACL
Anthology repository](https://github.com/acl-org/acl-anthology).  If you are
instantiating the Anthology for the first time, it might take a few seconds to
complete, as it will download around ~120 MB worth of data.  On subsequent
instantiations, it will look for updates and only download missing/updated data.

### From a folder on your machine

If you want to instantiate the Anthology from a local folder on your machine,
do:

```python
anthology = Anthology(datadir="/home/user/repos/acl-anthology/data")
```

This may be useful if you are working on your personal fork of the Anthology, or
a branch of the official repo.  The argument to `datadir` needs to point to a
data directory with the same structure as the [`data/` directory of the official
repo](https://github.com/acl-org/acl-anthology/tree/master/data).

## Examples

This section demonstrates how to use the `anthology` object by way of examples.

### Finding a paper by its ID

All metadata from the Anthology can be accessed through the `anthology` object.
For example, to obtain information about a specific paper, you can call
[`anthology.get()`][acl_anthology.anthology.Anthology.get] with the paper's
Anthology ID:

```pycon
>>> anthology.get("2022.acl-long.220")
Paper(
    id='220',
    bibkey='kitaev-etal-2022-learned',
    title=MarkupText('Learned Incremental Representations for Parsing'),
    authors=[
        NameSpecification(name=Name(first='Nikita', last='Kitaev'), id=None, affiliation=None, variants=[]),
        NameSpecification(name=Name(first='Thomas', last='Lu'), id=None, affiliation=None, variants=[]),
        NameSpecification(name=Name(first='Dan', last='Klein'), id=None, affiliation=None, variants=[])
    ],
    ...
)
```

All metadata fields are described in detail in {==TODO==}.

### Finding all papers by an author

{==TODO==}

### Finding all papers from an event

{==TODO==}

### Getting the BibTeX entry for a paper

{==TODO==}

### Searching for papers by keywords in title

{==TODO==}
