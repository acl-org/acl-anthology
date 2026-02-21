# Modifying Data

!!! danger

    This is currently still **work in progress.**


## Rules of thumb

**The aim of this library is to also make it easy to modify or create data in
the Anthology.**  The implementation of this is complicated by the various
indices and objects such as persons that cross-reference other objects.  Here
are some rules of thumb when making modifications to the data:

1. To **create new objects**, use `create_` functions provided by the library
   whenever possible, rather than instantiating them directly.
2. You can modify objects by simply **modifying their attributes**, as long as
   the object in question has an explicit representation in the Anthology data.
    - This includes collections, volumes, papers, events.
    - It also includes persons where `Person.is_explicit == True`, as those have
      an explicit representation in `people.yaml`.
3. **Saving data is always non-destructive**.  In XML files, it will also avoid
   introducing unnecessary changes (e.g. no needless reordering of tags).  The
   only exception to this is saving SIG YAML files, as they currently frequently
   contain comments, which will be lost when saving these files through the
   library.
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

    As a general rule, all classes perform **automatic input conversion and validation**.  This means that setting attributes should either "do the right thing" or raise a `TypeError`.  The main exception currently is modifying attributes in-place, e.g. appending to lists, as no input validation is performed then.

### Simple attributes

Attributes generally perform **input validation**.  For example, since a paper's
PDF attribute needs to be an instance of
[`PDFReference`][acl_anthology.files.PDFReference], trying to set it to a path
won't work and will raise a `TypeError`:

```pycon
>>> paper.pdf = Path("2025.test-1.pdf")  # TypeError
```

However, some attributes also provide **input converters** that perform simpler
conversions automatically.  For example, paper titles and abstracts are stored
as [`MarkupText`][acl_anthology.text.markuptext.MarkupText] objects, but setting
such an attribute to a string will automatically convert it:

```pycon
>>> paper.title = "Improving the ACL Anthology"
>>> paper.title
MarkupText('Improving the ACL Anthology')
```

The same applies to a [`Volume`][acl_anthology.collections.volume.Volume]'s year
of publication or date of ingestion, which both are stored as strings, but the
following will also work:

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

List attributes can be modified the same way as other attributes, however, there
is **no input validation or conversion** when modifying mutable attributes such
as lists, and no automatic tracking of modifications (see [Saving
changes](#saving-changes)) – only when _setting_ them.  Therefore, it is
recommended to _set_ list attributes every time you modify them.  For example,
to add an author to a paper, you can create a new
[`NameSpecification`][acl_anthology.people.name.NameSpecification] and append it
to the author list via `+=` (rather than `.append`), which will create a _new_
list and _set_ it on the attribute:

```pycon
>>> spec = NameSpecification("Bollmann, Marcel")
>>> paper.authors += [spec]
```

To change an existing author's name, you just need to remember that **names are
immutable**, so you need to modify the `NameSpecification` instead:

```pycon
>>> paper.authors[0].name.first = "Marc Marcel"             # will NOT work
>>> paper.authors[0].name = Name("Bollmann, Marc Marcel")   # works
```

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

??? info "A note on terminology"

    Within the library, the term **explicit** refers to a person that has an entry in `people.yaml`, whereas **inferred** refers to a person that was instantiated automatically while loading the XML data files (and has no entry in `people.yaml`).

    Currently, all inferred persons have IDs ending with `/unverified`, while IDs of explicit persons _must not_ end with `/unverified`.  (More specifically, they may not even contain a slash.)

    In practice, this means that "inferred" persons are currently equivalent to "unverified" persons, but the library intentionally uses terminology that is agnostic to the semantics of the ID.  If the semantics of whom we consider "(un)verified" change, the terminology in the library needn't change, as it only refers to the technical aspect of where the ID came from (`people.yaml` vs. implicit instantiation).

### Creating a new person

Manually creating a new person (that will get saved to `people.yaml` and can
have an ORCID and other metadata) can be done in two ways:

1. By calling [`PersonIndex.create()`][acl_anthology.people.index.PersonIndex.create].  The returned Person is _not_ linked to any papers/volumes, but you can set their ID afterwards on name specifications.

2. By calling [`make_explicit()`][acl_anthology.people.person.Person.make_explicit] on a currently _inferred_ person.  This will not only add this person to the database, but also **set their ID on all papers/volumes** currently associated with them.

### Example: Merging two persons

**Situation:** An author has published under multiple names, and therefore two separate persons get instantiated for them (let's call them `p1` and `p2`).  We want to merge them into a single person.

1. If neither person is _explicit_ yet: Call [`p1.make_explicit()`][acl_anthology.people.person.Person.make_explicit].  This will create an entry in `people.yaml` with all current names of `p1` add the new ID to all papers and volumes currently inferred to belong to either `p1`.

2. `p1` can now assumed to be explicit.  If `p2` is not explicit, call [`p2.merge_with_explicit(p1)`][acl_anthology.people.person.Person.merge_with_explicit].  This will add all of `p2`'s names to `p1` and set `p1`'s ID on all papers and volumes currently inferred to belong to `p2`.

3. Save the changes, e.g. via `Anthology.save_all()`.

### Example: Disambiguating a person

**Situation:** A person `p1` is currently associated with papers/volumes that actually belong to different people, who just happened to publish under the same name.  We want to create a new person instance for the other author with the same name.

1. Call [`anthology.people.create()`][acl_anthology.people.index.PersonIndex.create] for all persons who do not have an explicit ID yet, giving all the names that can refer to this person.  Also supply the ORCID when calling this function, if it is known.

2. For each person, go through the papers that actually belong to them and update the name specification where `namespec.id == p1` by setting the explicit ID of the correct newly-created person. {==TODO==}

## Ingesting new proceedings

Proceedings can be ingested almost entirely via functionality from this library;
in particular, no data files (XML or YAML) need to be saved manually.  _(The
only functionality that is currently not part of this library is the fixed-caser
for paper titles, which is described below.)_

### New collections, volumes, and papers

Creating new objects from `acl_anthology.collections` should be done with
`create_` functions from their respective parent objects.

All attributes that can be set on these objects (Volumes, Papers, etc.) can also
be supplied as keyword parameters to the `create_` functions.  Some required
attributes don't _need_ to be supplied here:

- A Paper's `id` will be set to the next-highest numeric ID that doesn't already
  exist in the volume, starting at `"1"`.
- A Paper's `bibkey` will be automatically generated if not explicitly set.
- A Volume's `year` attribute will be derived from the collection ID (e.g.,
  `"2049"` in a collection with ID `"2049.acl"`).
- A Volume's `type` will default to
  [PROCEEDINGS][acl_anthology.collections.types.VolumeType].

However, it is **strongly recommended to supply the author/editor list** when
calling a `create_` function, as this will resolve person IDs and create correct
bibkeys automatically.

!!! example

    Here is an example for how to create a new paper in an entirely new collection:

    ```python
    collection = anthology.create_collection("2049.acl")
    volume = collection.create_volume(
        id="long",
        title=MarkupText.from_latex_maybe("Proceedings of the ..."),
        venue_ids=["acl"],
    )
    paper = volume.create_paper(
        title=MarkupText.from_latex_maybe("GPT$^{\\infty}$ is all you need"),
        authors=[NameSpecification(first="John", last="Doe")],
    )
    ```

    When all volumes and papers have been added, the XML file is written by calling:

    ```python
    collection.save()
    ```

??? info "If you don't supply an author list here..."

    If you don't supply `authors` or `editors` when calling a `create_` function, or you need to modify those afterwards for some reason, you will need to perform these steps manually (which are otherwise handled by the `create_` function):

    - Call `anthology.people.ingest_namespec()` on each NameSpecification.
    - Call `refresh_bibkey()` on the Paper.

### Specifying titles and abstracts

Paper titles and abstracts are stored internally as [MarkupText][acl_anthology.text.markuptext.MarkupText], but it is possible to simply set them to a string value, in which case **heuristic markup conversion will be performed**.  Generally, for setting attributes that expect MarkupText, the following applies:

- Supplying a string value `s` is equivalent to using [`MarkupText.from_(s)`][acl_anthology.text.markuptext.MarkupText.from_], which will parse and convert simple markup.  Currently, only LaTeX markup is supported.

- If the heuristic conversion is not desired (or you want to make more explicit that you're converting from LaTeX), other builder methods of MarkupText can be used, such as [`MarkupText.from_latex()`][acl_anthology.text.markuptext.MarkupText.from_latex], or [`MarkupText.from_string()`][acl_anthology.text.markuptext.MarkupText.from_string] for plain strings

!!! example

    Setting a paper's title to a string automatically parses LaTeX markup contained in the string:

    ```pycon
    >>> paper.title = "Towards $\\infty$"
    >>> paper.title
    MarkupText('Towards <tex-math>\\infty</tex-math>')
    ```

    If this is not desired, MarkupText can be explicitly instantiated with one of its builder methods, for example:

    ```pycon
    >>> paper.title = MarkupText.from_string("Towards $\\infty$")
    >>> paper.title  # No markup parsing here
    MarkupText('Towards $\\infty$')
    ```

Paper titles should also have our **fixed-casing algorithm** applied to protect certain characters e.g. by wrapping them in braces in BibTeX entries.  **The fixed-caser is currently not part of this Python library.**  There are two options for running the fixed-casing on a new ingestion:

1. _Outside the ingestion script:_ Run [`bin/fixedcase/protect.py`](https://github.com/acl-org/acl-anthology/blob/master/bin/fixedcase/protect.py) on the new XML files produced by the ingestion script.

2. _Within the ingestion script:_ Convert titles to XML, run `fixedcase.protect()`, then set the title again from the modified XML element:

    ```python
    import fixedcase

    xml_title = paper.title.to_xml("title")
    fixedcase.protect(xml_title)
    paper.title = MarkupText.from_xml(xml_title)
    ```


### Specifying authors

Authors need to be specified by creating [name
specifications](accessing-authors.md#name-specifications), for example:

```python
NameSpecification(Name("Marcel", "Bollmann"), orcid="0000-0003-2598-8150")
```

If an ORCID is supplied, the NameSpecification also needs to have an explicit ID
referring to an entry in `people.yaml`.  **The library can add an ID
automatically** as long as you supply the author/editor list to the `create_`
function, so there is typically **no need to call `create()`** during
ingestion!

!!! example

    If you create a paper in the following way...

    ```python
    paper = volume.create_paper(
        title=MarkupText.from_string("The past and future of the ACL Anthology"),
        authors=[NameSpecification(Name("Marcel", "Bollmann"), orcid="0000-0003-2598-8150")],
    )
    ```

    ...the name specification will automatically be updated with an ID referring to this person in one of two ways:

    - If a person with this ORCID already exists in `people.yaml`, their ID will be filled in.
    - If a person with this ORCID does not exist in `people.yaml`, a new entry with this ORCID will be added to `people.yaml` with an auto-generated person ID.  The ID is a slug of the person's name; if necessary to avoid an ID clash, the last four digits of their ORCID will be appended.


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

Volumes can be connected to venues by modifying the volume's `venue_ids` list.
New venues can be added by calling
[`VenueIndex.create()`][acl_anthology.venues.VenueIndex.create], which will also
create a corresponding YAML file upon saving.  Afterwards, the ID used when
instantiating the venue can be used in a volume's `venue_ids`.

{==TODO: connecting to SIGs; we may want to refactor how SIGs are represented before introducing this functionality.==}


## Saving changes

!!! tip "Rule of thumb"

    Call [`anthology.save_all()`][acl_anthology.anthology.Anthology.save_all] to save all metadata changes.

Calling [`save_all()`][acl_anthology.anthology.Anthology.save_all] will write
XML and YAML files to the Anthology's data directory, with the following
caveats:

- **Collections will track if they have been modified** to prevent writing XML
  files unnecessarily.  As with modifying attributes in general, this requires
  that you have _set_ an attribute; modifying attributes in-place, e.g. lists,
  will not be detected.

  - Saving a collection manually can be done by calling
    [`Collection.save()`][acl_anthology.collections.collection.Collection.save].

  - Saving a collection uses a [minimal-diff
    algorithm][acl_anthology.utils.xml.ensure_minimal_diff] by default to avoid
    introducing "noise" in the diffs, i.e. changes to the XML that do not make a
    semantic difference, such as reordering certain tags, attributes, or
    introducing/deleting certain empty tags.  It is also guaranteed to be
    non-destructive through [integration tests on the entire Anthology
    data](https://github.com/acl-org/acl-anthology/blob/master/python/tests/anthology_integration_test.py).

- **YAML files will always be written**.  Serializing all YAML files is much
  faster than serializing all XML files, so they are written unconditionally,
  without tracking changes.

- **SIG YAML files are currently not written automatically**.  This is because
  the current format of the SIG YAML files is a bit arcane, and existing files
  use a lot of comments, which would be deleted upon writing these files.
  {==This may change in the future.==}
