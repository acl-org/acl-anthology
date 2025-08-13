# Modifying Data

!!! danger

    This is currently still **work in progress.**


## Rules of thumb

**The aim of this library is to also make it easy to modify or create data in
the Anthology.**  The implementation of this is complicated by the various
indices and objects such as persons that cross-reference other objects.  Here
are some rules of thumb when making modifications to the data:

1. To create new objects, use `create_` functions provided by the library
   whenever possible, rather than instantiating them directly.
2. You can modify objects by simply modifying their attributes, as long as the
   object in question has an explicit representation in the Anthology data.
    - This includes collections, volumes, papers, events.
    - It also includes persons where `Person.is_explicit == True`, as those have
      an explicit representation in `people.yaml`.
3. Saving data is always non-destructive and will avoid introducing unnecessary
   changes (e.g. no needless reordering of XML tags).  {==This is currently only
   true & tested for XML files, not for the YAML files.==}
4. If you need to refer to indices such as
   [PersonIndex][acl_anthology.people.index.PersonIndex],
   [EventIndex][acl_anthology.collections.eventindex.EventIndex], or
   [VenueIndex][acl_anthology.venues.VenueIndex] after making modifications, you
   should call
   [`Anthology.reset_indices()`][acl_anthology.anthology.Anthology.reset_indices]
   first.

## Modifying publications

To make modifications to existing publications, you can normally just modify the
attributes of the respective object.  For example, to add a DOI to paper, we can
just fetch the paper and set its `doi` attribute:

```pycon
>>> paper = anthology.get("2022.acl-long.99")
>>> paper.doi = '10.18653/v1/2022.acl-long.99'
```

!!! tip "Rule of thumb"

    For all `collections` objects, setting attributes should either raise a `TypeError`, or "do the right thing."  However, be careful when modifying _list_ attributes in-place, as no input validation is performed in that case.

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

### List attributes

List attributes can be modified the same way as other attributes; for example,
to add an author to a paper, you can create a new
[`NameSpecification`][acl_anthology.people.name.NameSpecification] and append it
to the author list:

```pycon
>>> spec = NameSpecification("Bollmann, Marcel")
>>> paper.authors.append(spec)
```

To change an existing author's name, you just need to remember that **names are
immutable**:

```pycon
>>> paper.authors[0].name.first = "Marc Marcel"             # will NOT work
>>> paper.authors[0].name = Name("Bollmann, Marc Marcel")   # works
```

There is **no input validation or conversion** when modifying mutable attributes
such as lists (only when _setting_ them).  That means you won't get an
immediate error if you e.g. append the wrong type of object to a list
attribute!

### Things to keep in mind

#### Citation keys
If a paper's title or author list has changed, you might want to recreate its
citation key (or 'bibkey').  This can be done by calling
[`Paper.refresh_bibkey()`][acl_anthology.collections.paper.Paper.refresh_bibkey].
If the auto-generated bibkey is identical to the current one, the bibkey will
not change.

#### Dependent indices
- If an item's `bibkey` changes, the [BibkeyIndex][acl_anthology.collections.bibkeys.BibkeyIndex] **will** update automatically.
- If an item's author or editor list changes, the [PersonIndex][acl_anthology.people.index.PersonIndex] and any [Person][acl_anthology.people.person.Person] objects created from it **will not update** automatically.
- If an item's `venue_ids` list changes, the [VenueIndex][acl_anthology.venues.VenueIndex] and any [Venue][acl_anthology.venues.Venue] objects created from it **will not update** automatically.
- If an item's `venue_ids` list changes, any implicit [Event][acl_anthology.collections.event.Event] created by it and its corresponding reverse-indexing in the [EventIndex][acl_anthology.collections.eventindex.EventIndex] **will not update** automatically.

If, after making changes, you need to access an index that is not updated automatically, just do:

```python
anthology.reset_indices()
```

This will _not_ update any Event, Person, or Venue objects you may have already
obtained, but any objects returned by an index _after_ the reset will reflect
the new data.


## Modifying people

A person can be _explicit_ (has an entry in `people.yaml`) or _inferred_ (was instantiated from a name specification without an ID).  To make modifications to persons, it is important to remember that:

1. Only an _explicit_ person's attributes can be meaningfully modified.

2. Changing which person a paper/volume is assigned to should be done by modifying the name specification on the paper/volume, not by changing anything on the Person object.

### Creating a new person

Manually creating a new person (that will get saved to `people.yaml` and can
have an ORCID and other metadata) can be done in two ways:

1. By calling [`PersonIndex.create_person()`][acl_anthology.people.index.PersonIndex.create_person].  The returned Person is _not_ linked to any papers/volumes, but you can set their ID afterwards on name specifications.

2. By calling [`make_explicit()`][acl_anthology.people.person.Person.make_explicit] on a currently _inferred_ person.  This will not only add this person to the database, but also **set their ID on all papers/volumes** currently associated with them.

### Merging two persons

**Situation:** An author has published on multiple names, but two separate persons get instantiated for them.  Let's call them `p1` and `p2`.

1. If neither of them are _explicit_ yet, we can start by calling `p1.make_explicit("their-new-author-id")`.  This will create an entry in `people.yaml` with all current names of `p1` and add the new ID to all papers and volumes currently inferred to belong to `p1`.

2. Iterate through `p2.papers()` and `p2.volumes()` and add `p1`'s new ID to the name specifications that are currently resolved to `p2`.  {==TODO: It's currently a bit tricky to find the _name specification_ referring to a person; might want to make this more convenient.==}

3. Save both the PersonIndex and the changed collections. {==TODO: A save-all function would be really convenient here.==}

### Disambiguating a person

**Situation:** A person is currently associated with papers/volumes that actually belong to different people.

{==TODO==}


## Ingesting new proceedings

{==TODO==}

### New collections, volumes, and papers

Creating new objects from `acl_anthology.collections` should be done with
`create_` functions from their respective parent objects.  Here is a minimal
example to create a new paper in an entirely new collection:

```python
collection = anthology.create_collection("2049.acl")
volume = collection.create_volume(
    id="long",
    title=MarkupText.from_string("Proceedings of the ..."),
)
paper = volume.create_paper(
    title=MarkupText.from_string("GPT-5000 is all you need")
)
```

All attributes that can be set on these objects can also be supplied as keyword
parameters to the `create_` functions, and it is **strongly recommended to
supply the author/editor list** here.

Some required attributes don't _need_ to be supplied on these functions:

- A Paper's `id` will be set to the next-highest numeric ID that doesn't already
  exist in the volume, starting at `"1"`.
- A Paper's `bibkey` will be automatically generated if not explicitly set.
- A Volume's `year` attribute will be derived from the collection ID (e.g.,
  `"2049"` in a collection with ID `"2049.acl"`).
- A Volume's `type` will default to
  [PROCEEDINGS][acl_anthology.collections.types.VolumeType].

??? info "If you don't supply an author list here..."

    If you don't supply `authors` or `editors` when calling a `create_` function, or you need to modify those afterwards for some reason, you will need to perform these steps manually (which are otherwise handled by the `create_` function):

    - Call `anthology.people.ingest_namespec()` on each NameSpecification.
    - Call `refresh_bibkey()` on the Paper.

### Specifying authors

Authors need to be specified by creating [name
specifications](accessing-authors.md#name-specifications), for example:

```python
NameSpecification(Name("Marcel", "Bollmann"), orcid="0000-0003-2598-8150")
```

If an ORCID is supplied, the NameSpecification also needs to have an explicit ID
referring to an entry in the author database (`people.yaml`).  **The library
handles this automatically** as long as you supply the author/editor list to the
`create_` function.

For example, if you create a paper in the following way...

```python
paper = volume.create_paper(
    title=MarkupText.from_string("The past and future of the ACL Anthology"),
    authors=[NameSpecification(Name("Marcel", "Bollmann"), orcid="0000-0003-2598-8150")],
)
```

...the name specification will automatically be updated with an ID referring to
the person with the supplied ORCID, creating this person (and a new person ID)
in `people.yaml` if necessary.

### New events

Creating an explicit event works the same way as with other collection items:

```python
event = collection.create_event(id="acl-2049")
```

An Event's `id`, if not given, will be automatically generated from the
collection ID (e.g., `"2049.acl"` will generate `"acl-2049"` for the event).

Since the mixture of implicit and explicit creation of events and linking them
to volumes can sometimes become a bit unintuitive (see [the documentation of
`create_event()`][acl_anthology.collections.collection.Collection.create_event]
or the source code of
[`EventIndex.load()`][acl_anthology.collections.eventindex.EventIndex.load] for
the gory details), it's best to ensure that:

1. The EventIndex has been loaded before creating a new event (e.g. by running
   `anthology.events.load()` or `anthology.load_all()`).
2. Any volumes in the same collection are explicitly added to the event via
   `event.add_colocated(volume)`.


### Connecting to venues and SIGs

{==TODO==}


### Parsing markup

MarkupText can be instantiated from strings representing LaTeX via
[`MarkupText.from_latex()`][acl_anthology.text.markuptext.MarkupText.from_latex].
This can be useful for titles and abstracts if they contain LaTeX commands, but
in practice, it may be unknown if they actually do.  In that case, using
[`MarkupText.from_latex_maybe()`][acl_anthology.text.markuptext.MarkupText.from_latex_maybe]
may be preferable, which will e.g. prevent percentage signs `%` from being
interpreted as starting a LaTeX comment, and apply a heuristic to decide if a
tilde `~` should be interpreted as a literal character or as a LaTeX
non-breaking space.

{==TODO: fixed-casing==}


## Saving changes

- **Changes to a collection/volume/paper** can be saved by calling
  [`Collection.save()`][acl_anthology.collections.collection.Collection.save].
  This will use a [minimal-diff
  algorithm][acl_anthology.utils.xml.ensure_minimal_diff] by default to avoid
  introducing "noise" in the diffs, i.e. changes to the XML that do not make a
  semantic difference, such as reordering certain tags, attributes, or
  introducing/deleting certain empty tags.  It is also guaranteed to be
  non-destructive through [integration tests on the entire Anthology
  data](https://github.com/acl-org/acl-anthology/blob/master/python/tests/anthology_integration_test.py).

- **Changes to the person database (`people.yaml`)** can be saved by calling
  [`PersonIndex.save()`][acl_anthology.people.index.PersonIndex.save].

{==TODO: changes to other YAML files, `Anthology.save_all()`, etc. ==}
