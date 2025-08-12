# Data indexing

As [outlined in the original design decisions](design.md#data-indexing), many
operations on the Anthology require loading the entire data files in order to
build indices from them.  This document collects thoughts on the implementation
and optimization of indexing.

## Building an index and keeping it updated

An index is a mapping of some attribute to some object.  For example, the
[BibkeyIndex][acl_anthology.collections.bibkeys.BibkeyIndex] maps strings
(representing bibkeys) to [Paper][acl_anthology.collections.paper.Paper]
objects.  Like all data-accessing objects, an index should be built lazily,
i.e. only when it is actually accessed.

When considering **read-only access** to the data, building the index is
straight-forward:

- Use [SlottedDict][acl_anthology.containers.SlottedDict]'s lazy-loading
  mechanism to gate all access to the data.
- On `.load()`, iterate through all collections and construct the index.

When considering **modifying data**, there is the added challenge of keeping
indices updated.  It should be convenient to modify data by simply changing
attributes of the objects; for example, it should be easy to update a bibkey by
simply setting `paper.bibkey` to something else.  However, in this example, the
BibkeyIndex would need to be updated to _remove the old attribute_ and to
_re-index the paper with the new attribute_.  Where and how should this be
triggered?

A similar situation is **adding new data**, e.g. when ingesting new
proceedings. There are (at least) two different ways to model how an ingestion
script should operate:

1. Directly instantiate `Collection`, `Volume`, and `Paper` objects from the
   ingestion script.  This feels nice and clean in terms of the API, but raises
   the question how the indices get notified of newly created objects.
2. Call builder functions, such as `Volume.create_new_paper()`, to create new
   objects.  This creates more overhead in the API, but allows us to update the
   relevant indices within the builder function.  It also logically separates
   the creation of objects _when loading from XML_ and _when ingesting new
   material_.

### Current solution

- When **reading data** from the XML, each index constructs itself in its
  respective `.load()` or `.build()` function.  It is only constructed when it
  is actually accessed.

- When **modifying data** after it has been read from the XML, the fields that
  have been modified are responsible for updating any indices that depend on
  them.  This is achieved by using the `on_setattr` functionality of
  [attrs.field][], which triggers when a field is assigned a new value, _but not
  on first initialization_.

    - When a dependent index has not yet been loaded, it should not need to be
      updated.  Loading the index should loop through all relevant objects in
      memory anyway, so the modified value will be indexed when the index is
      loaded normally.

- When **adding data** that is not in the XML, builder functions such as
  [Volume.create_paper()][acl_anthology.collections.volume.Volume.create_paper]
  should always be used over instantiating objects directly.  The builder
  functions are responsible for updating any indices that are affected by the
  newly created object.
