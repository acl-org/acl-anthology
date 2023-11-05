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
Github](https://github.com/acl-org/acl-anthology/releases/).

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

For more information on the provided metadata fields, see [Types of Metadata](types-of-metadata.md).

### Finding all papers by an author

To find a person by name, you can use [`anthology.find_people()`][acl_anthology.anthology.Anthology.find_people]:

```pycon
>>> results = anthology.find_people("Dan Klein")
```

Note that this will _always_ return a **list** of
[`Person`][acl_anthology.people.person.Person] objects, as names can be
ambiguous.  For now let's assume there is only one, and get all their
publications:

```pycon
>>> person = results[0]
>>> person.item_ids
{
    ('P18', '2', '75'),
    ('P17', '2', '52'),
    ('2023.acl', 'short', '65'),
    ...
}
>>> for paper in person.papers():
...     print(paper.title)
...
Policy Gradient as a Proxy for Dynamic Oracles in Constituency Parsing
Fine-Grained Entity Typing with High-Multiplicity Assignments
Modular Visual Question Answering via Code Generation
...
```

If you know the _internal ID_ of the person (which is what appears in the URL
for their author page, e.g.,
[https://aclanthology.org/people/d/dan-klein/](https://aclanthology.org/people/d/dan-klein/)),
you can find the corresponding [`Person`][acl_anthology.people.person.Person]
object directly:

```pycon
>>> person = anthology.get_person("dan-klein")
```

If you want to look up a person based on the "author" or "editor" field of an
existing paper, you are working with a
[`NameSpecification`][acl_anthology.people.name.NameSpecification], which is a
name that may additionally contain information to help disambiguate it from
similar names.  In this case, you can call
[`anthology.resolve()`][acl_anthology.anthology.Anthology.resolve], which will
always return a single, uniquely identified person:

```pycon
>>> paper = anthology.get("2022.acl-long.220")
>>> paper.authors[-1]
NameSpecification(name=Name(first='Dan', last='Klein'), ...)
>>> person = anthology.resolve(paper.authors[-1])
```

[Accessing Authors/Editors](accessing-authors.md) describes the intricacies of
working with names and people in more detail.

### Finding all papers from an event

Volumes that were presented at the same conference are grouped together under
[`Event`][acl_anthology.collections.event.Event] objects.  For example, here is
[ACL 2022](https://aclanthology.org/events/acl-2022/) and all volumes that
belong to the conference or to colocated workshops:

```pycon
>>> event = anthology.get_event("acl-2022")
>>> event
Event(
    id='acl-2022',
    is_explicit=True,
    colocated_ids=<list of 34 AnthologyIDTuple objects>,
    title=MarkupText('60th Annual Meeting of the Association for Computational Linguistics'),
    location='Dublin, Ireland',
    dates='May 22–27, 2022'
)
>>> for volume in event.volumes():
...     print(volume.title)
...
Proceedings of the 60th Annual Meeting of the Association for Computational Linguistics (Volume 1: Long Papers)
Proceedings of the 60th Annual Meeting of the Association for Computational Linguistics (Volume 2: Short Papers)
Proceedings of the 60th Annual Meeting of the Association for Computational Linguistics: Student Research Workshop
Proceedings of the 60th Annual Meeting of the Association for Computational Linguistics: System Demonstrations
Proceedings of the 60th Annual Meeting of the Association for Computational Linguistics: Tutorial Abstracts
Findings of the Association for Computational Linguistics: ACL 2022
Proceedings of BigScience Episode #5 -- Workshop on Challenges & Perspectives in Creating Large Language Models
Proceedings of the 21st Workshop on Biomedical Language Processing
...
```

If you don't know the event ID(s), you can also get associated event IDs from a
paper or volume.  Here, we find out that
[2020.blackboxnlp-1](https://aclanthology.org/volumes/2020.blackboxnlp-1/)
belongs to its "own" event (`blackboxnlp-2020`), the generic "workshops in 2020"
event (`ws-2020`), as well as the EMNLP 2020 event.

```pycon
>>> volume = anthology.get("2020.blackboxnlp-1")
>>> volume.get_events()
[
    Event(id='blackboxnlp-2020', colocated_ids=<list of 1 AnthologyIDTuple objects>, ...),
    Event(id='ws-2020', colocated_ids=<list of 105 AnthologyIDTuple objects>, ...),
    Event(id='emnlp-2020', colocated_ids=<list of 27 AnthologyIDTuple objects>, ...)
]
```

<!-- {==What about SIGs or venues? No way to find all papers yet==} -->

### Getting the BibTeX entry for a paper

To generate the BibTeX entry for a paper, simply call [`Paper.to_bibtex()`][acl_anthology.collections.paper.Paper.to_bibtex]:

```pycon
>>> paper = anthology.get("2022.acl-long.220")
>>> print(paper.to_bibtex())
@inproceedings{kitaev-etal-2022-learned,
    title = "Learned Incremental Representations for Parsing",
    author = "Kitaev, Nikita  and
      Lu, Thomas  and
      Klein, Dan",
    editor = "Muresan, Smaranda  and
      Nakov, Preslav  and
      Villavicencio, Aline",
    booktitle = "Proceedings of the 60th Annual Meeting of the Association for Computational Linguistics (Volume 1: Long Papers)",
    month = may,
    year = "2022",
    address = "Dublin, Ireland",
    publisher = "Association for Computational Linguistics",
    url = "https://aclanthology.org/2022.acl-long.220/",
    doi = "10.18653/v1/2022.acl-long.220",
    pages = "3086--3095"
}
```

To also include the abstract in the BibTeX entry:

```pycon
>>> print(paper.to_bibtex(with_abstract=True))
```

### Searching for papers by keywords in title

There is no dedicated search index for paper titles, but you can iterate over
papers and compare their titles manually.  For example, the following code finds
all papers containing the substring "semantic parsing" in their title, and
prints their Anthology IDs and full titles:

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
