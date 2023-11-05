# Design decisions

The ACL Anthology comes with its own [Python
library](https://github.com/acl-org/acl-anthology/tree/master/bin/anthology)
that is used for building the website.  When I first made it, the focus was on
*preserving functionality* of the scripts that existed before it.  Over time, it
became clear that the library has some drawbacks: most notably, [it's very
slow](https://github.com/acl-org/acl-anthology/issues/835), a problem that is
only going to get worse as the number of papers in the Anthology grows.  The
tight coupling with the website build chain also causes some obstacles for
[turning it into a PyPI
package](https://github.com/acl-org/acl-anthology/issues/913).

The XML data of the Anthology, which a library should provide access to, is in a
much cleaner state now and [documented with an enforced RelaxNG
schema](https://github.com/acl-org/acl-anthology/tree/master/data/xml/schema.rnc).
This project is an attempt to design a Python library from scratch based on the
data format described in this schema.

In the following, I describe some design decisions that guide the development of
this library.


## Data source

The main entrypoint to the library will be a single `Anthology()` object that
accesses the Anthology's data source.  This data source could come from two places:

1. A local directory.  This is useful when building the ACL Anthology website,
   debugging, or using the library to make changes to the Anthology data.  The
   data directory can be given as an argument when instantiating the
   `Anthology()` class.

2. A git repository.  This is useful when fetching the library via PyPI with the
   aim of working with the official ACL Anthology data.

    - The library could use
      [GitPython](https://gitpython.readthedocs.io/en/stable/) to interact with
      the [official ACL Anthology
      repo](https://github.com/acl-org/acl-anthology/).  Maybe it is even
      sufficient to download just the `data/` directory from the repo.
    - The directory to store the Anthology data can be determined in a
      system-specific way using libraries such as
      [platformdirs](https://pypi.org/project/platformdirs/), meaning the library
      "just works" without the need for the user to provide a specific data
      directory.
    - The library needs to check for updates to the Anthology data from time to
      time. This should be configurable and default to a reasonable value, e.g.,
      once every 24 hours.

## Data indexing

The data files in the repo effectively provide:

- An index of Anthology IDs to volumes, papers, and events (by way of file
  naming conventions).
- An index of venues and SIGs to the direct metadata (title, etc.) about them.

What is missing, and **currently very time-consuming** when instantiating the
Anthology, is an index from all other associated objects back to individual
papers, particularly:

- An index of people to associated volumes/papers.
- An index of names to their canonical IDs, and vice versa.
- An index of venues and events to associated volumes/papers.

Currently, it is hard to defer and/or cache these computations, as they all
happen during the initial instantiation of the Anthology class, and map entries
to `Paper` objects, requiring all these `Paper` objects to be instantiated as
well.

The new library should:

1. Construct these indices to use **Anthology IDs as values**, so that they can
   be serialized independently of the volume/paper objects. This enables both
   **serialization** and **lazy loading** of the respective volume/paper data.

2. **Cache the indices to disk** so that the costly computation step only needs
   to be performed when the underlying data source changes.

    - This needs an appropriate mechanism for ensuring that an index is
      up-to-date with respect to a given data source.

### Lazy loading

Having data indices as the primary structures through which Anthology data is
accessed means that the XML files themselves only need to be **loaded
on-demand**.

This could mean:

- When a volume is accessed (e.g. an iterator of papers), the XML file is loaded
  and parsed at that time.

- When a specific paper is accessed (e.g. through an author's publications, or
  by specifically accessing a given paper ID), either the entire XML file could
  be loaded at that point in time, or only the specific paper in question
  (e.g. through XPath expressions).

## Data access

Currently, most of the data fields for people, papers, and volumes are
**computed on instantiation** of the corresponding object, rather than when the
information is actually needed. A lot of crucial information is also stored in a
`.attrib` dictionary, making it hard to reason about which attributes are/should
be present.

The new library should:

1. Encapsulate all data access through **explicit class properties**.

2. **Defer non-trivial computation** of such class properties until the time
   they are actually being accessed.

## Data validation

In the interest of runtime performance for the library's most common use case —
reading and parsing the official Anthology XML data — there should be **no
validation of any data** by default. Data will be assumed to be correct and
well-formed, as this is ensured by a variety of checks on the upstream ACL
Anthology repo.

To make the library more useful for _modifying_ Anthology data, e.g. as part of
ingestion or correction scripts, separate validation methods can be added that
can be called on-demand.
