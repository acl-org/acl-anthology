# ACL Anthology - Detailed Instructions

These are the detailed instructions on generating the ACL Anthology website as
seen on <https://aclanthology.org/> and contributing to it.


## Generating the Anthology

The Anthology website is generated using the [Hugo](https://gohugo.io) static
site generator.  However, before we can actually invoke Hugo, we need to prepare
the contents of the website.  The following steps describe what happens behind
the scenes.  All the steps have a corresponding `make` target as well.  To build
the entire website, you can simply run:

```bash
make site
```

If this doesn't work, you can instead use the following instructions to go through
the process step by step and observe the expected outputs.

> [!WARNING]
> As of February 2026, building the website will generate ca. 18 GB of extra
> data in 522,000 separate files on your hard drive.  This amount will grow as
> more proceedings are added to the Anthology.

### Step 0: Install prerequisites

#### Required dependencies

+ [**uv**](https://docs.astral.sh/uv/getting-started/installation/) manages the
  Python library and other Python dependencies.
+ [**Hugo 0.154.0 (extended version)**](https://gohugo.io/installation/) is the
  static site generator that builds the website.
+ [**Dart Sass**](https://sass-lang.com/install/), a CSS extension that is
  needed by Hugo.

#### Optional dependencies

+ [**bibutils**](https://sourceforge.net/p/bibutils/home/Bibutils/) creates
  non-BibTeX citation formats (not strictly required to build the website, but
  these citation formats will be missing otherwise).
+ [**jing**](https://github.com/relaxng/jing-trang) is a RELAX NG validator that
  checks that XML files conform to the schema; required for running checks.
+ [**just**](https://just.systems/man/en/) is a command runner that can be used
  to invoke some "recipes" defined in the repo, which provides some convenience.

#### Installation

All of these dependencies can be installed via Homebrew:

```bash
brew install bibutils hugo jing-trang just sass/sass/sass uv
```

If you're not on a system that uses Homebrew, refer to the linked websites above
for installation instructions.

### Step 1: Prepare the data for site generation

The data sources for the Anthology reside in the [`data/`](data/) directory.
XML files contain the authoritative paper metadata, and additional YAML files
document information about authors, venues, and special interest groups (SIGs).
Before the Anthology website can be generated, all this information needs to be
converted and preprocessed for the static site generator.  Some derived
information, such as BibTeX entries for each paper, is also added in this step.

This step can be run separately by calling `make hugo_data`, which runs the
[`bin/create_hugo_data.py`](bin/create_hugo_data.py) script, and should not take
longer than a few minutes.  Manually, it can be run via:

```bash
uv run python bin/create_hugo_data.py --clean
```

### Step 2: Create extra bibliography export files for papers

> [!TIP]
> This step is skipped on preview branches, and can also be skipped in local
> builds by setting `NOBIB=true`, e.g. `make NOBIB=true all`.

In this step, we create the full consolidated BibTeX files (`anthology.bib`
etc.) as well as the MODS and Endnote formats.  For other export formats, we
rely on the [`bibutils`](https://sourceforge.net/p/bibutils/home/Bibutils/)
suite by first converting the generated `.bib` files to MODS XML, then
converting the MODS XML to Endnote.  We use some performance optimizations (such
as process pools) to speed this up.

This step can be run separately by calling `make bib`, which runs the
[`bin/create_extra_bib.py`](bin/create_extra_bib.py) script.  Manually, it can
be run via:

```bash
uv run python bin/create_extra_bib.py --clean
```

The exported files will be written to the `build/data-export/` subdirectory.

### Step 3: Run Hugo

The files that were generated so far are in the `build/` subdirectory, in which
Hugo will be invoked. Before doing this, however, we need to also copy the
content of the `hugo/` subdirectory into `build/` so that all the configuration
files and the page structure is accessible to the engine.  Afterwards, the
website can be built by invoking `hugo` from the `build/` subdirectory:

```bash
cp -r hugo/* build
cd build/ && hugo --cleanDestinationDir --minify
```

Generating the website is quite a resource-hungry process, but should not take
longer than a few minutes.  Due to the high memory usage, it is possible that it
will cause swapping and consequently slow down your system for a while, though
recent versions of Hugo have become quite efficient at running periodic garbage
collection to keep memory usage low (ca. 13 GB).

The fully generated website will be in `build/website/` afterwards.


## Making changes to the Anthology

The static site tries to follow a strict *separation of content and
presentation.* If you need to make changes to the Anthology, the first step is
to figure out *where* to make these changes.

Changes in **content** (paper metadata, information about SIGs, etc.) should
always be made in the data files under `data/` or in the scripts that
interpret them; changes that only affect the **presentation** on the website can
be made within the Hugo templates.

### Content (Data Files)

The data sources of the Anthology are currently stored under `data/`.  They
comprise:

+ The authoritative XML files (in [`xml/`](data/xml)); these contain all paper
  metadata.  Their format is defined in a RELAX NG schema
  [`schema.rnc`](data/xml/schema.rnc) in the same directory.

+ YAML files for SIGs (in [`yaml/sigs/`](data/yaml/sigs)); these contain names,
  URLs, and associated venues for all Special Interest Groups (SIGs).

+ YAML files that define venues (in [`yaml/venues/`](data/yaml/venues)).
  Each venue has its own YAML file that contains venue-specific information
  such as acronym, full name and URL.

+ An author index ([`people.yaml`](data/yaml/people.yaml)) that defines all
  [verified authors](hugo/content/info/verification.md), together with metadata
  such as ORCID iDs and all [known name variants](hugo/content/info/names.md).

**The `acl_anthology` Python library** under [`python/`](python/) is responsible
for parsing and interpreting all these data files, and **is the recommended way
of making modifications to them** – see the [documentation of the Python
library](https://acl-anthology.readthedocs.io/) and the [guide for modifying
data](https://acl-anthology.readthedocs.io/latest/guide/modifying-data/).

Some information that is not explicitly stored in any of these files is *derived
automatically* by this library during Step 1 of building the website.

### Presentation (Templates)

HTML templates for the website are found under [`hugo/layouts/`](hugo/layouts/).

+ The main skeleton for all HTML files is
  [`_default/baseof.html`](hugo/layouts/_default/baseof.html).

+ The front page is [`index.html`](hugo/layouts/index.html).

+ Most other pages are defined as `**/single.html` (e.g.,
  [`papers/single.html`](hugo/layouts/papers/single.html) defines the paper
  pages).

+ The appearance of paper entries in lists (on proceedings pages, author pages,
  etc.) is defined in
  [`papers/list-entry.html`](hugo/layouts/papers/list-entry.html).

CSS styling for the website is based on [Bootstrap
5.3](https://getbootstrap.com/docs/5.3/).  The final CSS is compiled from
[`hugo/assets/css/main.scss`](hugo/assets/css/main.scss), which defines

1. which Bootstrap components to include,
2. which Bootstrap variables to customize (e.g. colors), and
3. additional style definitions on top of that.

We use the [Inter](https://rsms.me/inter/) font family, which is self-hosted
within the repository to ensure visual consistency and privacy.

> [!TIP]
> For making changes to the Hugo templates (or CSS styling), it can be useful
> to preview the website locally with Hugo's built-in webserver, which watches
> the files (in `build/`) for changes and automatically rebuilds the site.
> You can invoke this most easily via `just serve`.  Note that you will have to
> develop your changes inside the `build/` folder and copy them back to the
> `hugo/` folder afterwards.

### Adding new years to the Anthology

If a new year is added to the Anthology, make sure the [front page
template](hugo/layouts/index.html) is updated to include this new year.  Make
sure to adjust the variable `$all_years` (and `$border_years`, if needed) and
don't forget to **update the table headers** as well!  (Their `colspan`
attributes need to match the number of years subsumed under the header.)


## Testing & coding style

The following criteria are checked automatically (via [pre-commit
hooks](.pre-commit-config.yaml) that are run within GitHub workflows) and
enforced for all changes pushed to the Anthology:

1. YAML files need to be syntactically well-formed.
2. XML files need to follow the schema definition in
   [`schema.rnc`](data/xml/schema.rnc).
3. Files should end in exactly one newline, and lines should not have trailing
   whitespace.
4. Python files should have a maximum line length of 90 and follow the linting
   and formatting rules defined by the
   [`ruff`](https://github.com/charliermarsh/ruff) tool.  If there's a good
   reason to ignore a rule, [`noqa`
   comments](https://docs.astral.sh/ruff/configuration/#error-suppression) can
   be used on an individual basis.

These checks can be run on *all files in the repository* via `make check`, which
will invoke `uv run pre-commit run --all-files`.

**Before committing to this repo,** it is strongly recommended that you set up
the pre-commit hooks to run on every attempted commit:

```bash
uv run pre-commit install
```

The first time you run pre-commit, the hooks will be downloaded and installed,
which may take a short while.  However, the actual pre-commit hooks will only
run on files *currently staged for commit*, which should not introduce
noticeable delays most of the time.

Some pre-commit hooks will **automatically modify ("fix") files** when they
encounter issues.  These changes need to be explicitly staged before the next
commit attempt, so you can always review (and potentially undo) what the hooks
do to your files before you commit.

### Integration tests of the Python library

The `acl_anthology` library contains an extensive test suite that includes
[integration tests](python/tests/anthology_integration_test.py), which test,
among other things, that (i) there is no error loading the data files with the
library, and that (ii) loading and saving the data files is a non-destructive
operation that does not introduce unexpected changes.  The latter also requires
that XML files follow a consistent, pre-defined formatting scheme (e.g. correct
indentation, no unnecessary HTML entities).

As the integration tests are more time-intensive to run, they are _not_ included
in the pre-commit checks.  However, they _will_ be run via GitHub workflows
during a build check.  If you modify data files and want to ensure that the
integration tests pass, they can be run via:

```bash
just python test-integration
```
