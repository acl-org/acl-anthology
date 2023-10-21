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

All metadata from the Anthology can be accessed through the
[`anthology`][acl_anthology.anthology.Anthology] object.  For example, to obtain
information about a specific paper, you can call
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

To find a person by name, you can use [`anthology.find_people()`][acl_anthology.anthology.Anthology.find_people]:

```pycon
>>> people = anthology.find_people("Dan Klein")
```

Note that this will **_always_** return a _list_ of people, as names can be ambiguous.  For now let's assume there is only one, and get all their publications:

```pycon
>>> person = results[0]
>>> person.item_ids
{
    ('P18', '2', '75'),
    ('P17', '2', '52'),
    ('2023.acl', 'short', '65'),
    ('2020.emnlp', 'main', '445'),
    ('P16', '1', '188'),
    ('2023.acl', 'long', '91'),
    ...
}
>>> for id_ in person.item_ids:
...     print(anthology.get(id_).title)
...
Policy Gradient as a Proxy for Dynamic Oracles in Constituency Parsing
Fine-Grained Entity Typing with High-Multiplicity Assignments
Modular Visual Question Answering via Code Generation
Digital Voicing of Silent Speech
...
```

If you know the _internal ID_ of the person (which is what appears in the URL for their author page, e.g., [https://aclanthology.org/people/d/dan-klein/][]), you can interact with the [`PersonIndex`][acl_anthology.people.index.PersonIndex] directly:

```pycon
>>> person = anthology.people.get("dan-klein")
>>> person = anthology.get_person("dan-klein")  # equivalent
```

If you want to look up a person based on the "author" or "editor" field of an existing paper, you are working with a [`NameSpecification`][acl_anthology.people.name.NameSpecification], which is a name that may additionally contain information to help disambiguate it from similar names.  In this case, you can call [`anthology.resolve()`][acl_anthology.anthology.Anthology.resolve], which will always return a single, uniquely identified person:

```pycon
>>> paper = anthology.get("2022.acl-long.220")
>>> paper.authors[-1]
NameSpecification(name=Name(first='Dan', last='Klein'), id=None, affiliation=None, variants=[])
>>> person = anthology.resolve(paper.authors[-1])
```

{==TODO==} describes the intricacies of working with names and people in more detail.

### Finding all papers from an event

{==TODO==}

```pycon
>>> event = anthology.events.get("acl-2022")
>>> event
Event(
    id='acl-2022',
    is_explicit=True,
    title=MarkupText('60th Annual Meeting of the Association for Computational Linguistics'),
    location='Dublin, Ireland',
    dates='May 22–27, 2022'
)
>>> event.colocated_ids
[
    ('2022.acl', 'long', None),
    ('2022.acl', 'short', None),
    ('2022.acl', 'srw', None),
    ('2022.acl', 'demo', None),
    ('2022.acl', 'tutorials', None),
    ('2022.findings', 'acl', None),
    ('2022.bigscience', '1', None),
    ('2022.bionlp', '1', None),
    ...
]
```

{==What if you don't know the event ID?==}

```pycon
>>> volume = anthology.get_volume("2022.bigscience-1")
>>> # Currently no way to find the event that contains this!
```

{==What about SIGs or venues? No way to find all papers yet==}

### Getting the BibTeX entry for a paper

{==TODO==}

```pycon
>>> paper = anthology.get("2022.acl-long.220")
>>> # TODO: Not currently possible yet
```

### Searching for papers by keywords in title

The following example prints all Anthology IDs and titles of papers that
contain the substring "semantic parsing" in their title:

```pycon
>>> for paper in anthology.papers():
...     if "semantic parsing" in str(paper.title).lower():
...         print(paper.full_id, paper.title)
...
2007.tmi-papers.10 Learning bilingual semantic frames: shallow semantic parsing vs. semantic role projection
2020.acl-main.427 CraftAssist Instruction Parsing: Semantic Parsing for a Voxel-World Assistant
2020.acl-main.606 Semantic Parsing for English as a Second Language
2020.acl-main.608 Unsupervised Dual Paraphrasing for Two-stage Semantic Parsing
2020.acl-main.742 Exploring Unexplored Generalization Challenges for Cross-Database Semantic Parsing
2020.acl-main.746 Universal Decompositional Semantic Parsing
2020.acl-demos.29 Usnea: An Authorship Tool for Interactive Fiction using Retrieval Based Semantic Parsing
2020.alta-1.16 Transformer Semantic Parsing
2020.coling-main.226 Context Dependent Semantic Parsing: A Survey
...
```

Note how the comparison calls `str()` on `paper.title` to obtain the title as a
string.  This is because paper titles can contain _markup_, and therefore need
to be explicitly converted to strings first if you want to perform string
operations on them.
