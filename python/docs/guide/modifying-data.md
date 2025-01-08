# Modifying Data

!!! danger

    This is currently still **work in progress.**


## Modifying publications

To make modifications to existing publications, you can normally just modify the
attributes of the respective object.  For example, to add a DOI to paper, we can
just fetch the paper and set its `doi` attribute:

```pycon
>>> paper = anthology.get("2022.acl-long.99")
>>> paper.doi = '10.18653/v1/2022.acl-long.99'
```

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

As a general rule, modifying attributes of `collections` objects should either
raise a `TypeError`, or "do the right thing."

{==TODO: This is currently not true for list attributions such as author lists.  Needs further development.==}

## Modifying people

{==TODO==}


## Ingesting new proceedings

{==TODO==}


## Saving changes

{==TODO==}
