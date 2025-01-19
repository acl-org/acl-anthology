# Modifying Data

!!! danger

    This is currently still **work in progress.**


## Rules of thumb

The aim of this library is to also make it easy to modify or create data in the
Anthology.  This is complicated by the various indices and objects such as
persons that cross-reference other objects.  Here are some rules of thumb when
making modifications to the data:

1. To create new objects, use `create_` functions provided by the library
   whenever possible, rather than instantiating them directly.
2. You can modify objects by simply modifying their attributes, as long as the
   object in question has an explicit representation in the Anthology data.
    - This includes collections, volumes, papers, events, but not e.g. persons.
3. If you need to refer to indices such as
   [PersonIndex][acl_anthology.people.index.PersonIndex],
   [EventIndex][acl_anthology.collections.eventindex.EventIndex], or
   [VenueIndex][acl_anthology.venues.VenueIndex] after making modifications, you
   should call
   [`Anthology.reset_indices()`][acl_anthology.anthology.Anthology.reset_indices]
   first.

{==TODO: how/where to call `save()`==}

## Modifying publications

To make modifications to existing publications, you can normally just modify the
attributes of the respective object.  For example, to add a DOI to paper, we can
just fetch the paper and set its `doi` attribute:

```pycon
>>> paper = anthology.get("2022.acl-long.99")
>>> paper.doi = '10.18653/v1/2022.acl-long.99'
```

### Simple attributes

Attributes generally perform **input validation**.  For example, since a paper's
title needs to be a [`MarkupText`][acl_anthology.text.markuptext.MarkupText],
the following won't work and will raise a `TypeError`:

```pycon
>>> paper.title = "Computational Historical Linguistics and Language Diversity"
```

However, some attributes also provide **input converters** that perform simpler
conversions automatically.  For example, a
[`Volume`][acl_anthology.collections.volume.Volume]'s year of publication or
date of ingestion is stored as a string, but the following will also work:

```pycon
>>> volume = anthology.get("2022.acl-long")
>>> volume.year = 2022
>>> volume.year
'2022'
>>> from datetime import date
>>> volume.ingest_date = date.today()
>>> volume.ingest_date
'2025-01-08'
```

As a general rule, setting attributes of `collections` objects should either
raise a `TypeError`, or "do the right thing."

### List attributes

List attributes can be modified the same way as other attributes; for example,
to add an author to a paper, you can create a new
[`NameSpecification`][acl_anthology.people.name.NameSpecification] and append it
to the author list:

```pycon
>>> spec = NameSpecification("Bollmann, Marcel")
>>> paper.authors.append(spec)
```

To change an existing author's name, you just need to remember that names are
immutable:

```pycon
>>> papers.authors[0].name = Name("Bollmann, Marcel")
```

!!! danger

    Input validation or conversion cannot be done when _modifying_ mutable
    attributes such as lists (only when _setting_ them).  That means you won't
    get an (immediate) error if you e.g. append the wrong type of object to a
    list attribute.

## Modifying people

{==TODO==}


## Ingesting new proceedings

{==TODO==}


## Saving changes

{==TODO==}
