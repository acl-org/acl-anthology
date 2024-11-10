# ACL Anthology - Detailed Instructions

These are the detailed instructions on generating the ACL Anthology website as
seen on <https://aclanthology.org/> and contributing to it.


## Generating the Anthology

The Anthology website is generated using the [Hugo](https://gohugo.io) static
site generator.  However, before we can actually invoke Hugo, we need to prepare
the contents of the website.  The following steps describe what happens
behind the scenes.  All the steps have a corresponding `make` target as well.
If you are on a system that uses `apt` for installing packages, you can therefore
just run the following commands:

```bash
sudo apt install jing libyaml-dev bibutils hugo
make all
```

If this doesn't work, you can instead use the following instructions to go through
the process step by step and observe the expected outputs.

### Step 0: Install required Python packages
To build the anthology, the packages listed in
  [bin/requirements.txt](bin/requirements.txt) are needed (they are installed and updated by make automatically).
  + *Note:* You can install all needed dependencies using the command `pip install -r bin/requirements.txt`
  + *Note:* [Installing the PyYAML package with C
    bindings](http://rmcgibbo.github.io/blog/2013/05/23/faster-yaml-parsing-with-libyaml/)
    will speed up the generation process.  On Debian-based systems, you have to do
	the following if `libyaml-dev` was not installed before running make the first time:
	`sudo apt install libyaml-dev`, enable virtualenv: `source venv/bin/activate` and
	rebuild pyyaml with libyaml backend: `pip3 install pyyaml --upgrade --force`.
    If this doesn't enable the C bindings, make sure you have Cython installed,
    then try rebuilding pyyaml again.

You also need to install "jing", an XML schema checker. if you are using Homebrew on OS X, you can install
this with `brew install jing-trang`.

### Step 1: Prepare the data for site generation

The data sources for the Anthology currently reside in the [`data/`](data/)
directory.  XML files contain the authoritative paper metadata, and additional
YAML files document information about venues and special interest groups (SIGs).
Before the Anthology website can be generated, all this information needs to be
converted and preprocessed for the static site generator.

This is achieved by calling:

```bash
$ python3 bin/create_hugo_yaml.py
```

This process should not take longer than a few minutes and can be sped up
considerably by [installing PyYAML with C
bindings](http://rmcgibbo.github.io/blog/2013/05/23/faster-yaml-parsing-with-libyaml/).

### Step 2: Create page stubs for site generation

The YAML files created in Step 1 are used by Hugo to pull in information about
venues/papers/etc., but they cannot be used to define what actual *pages* the
website should have.  Therefore, another script takes the YAML files generated
in Step 1 and produce stubs of pages for each individual paper, venue, etc.

This is achieved by calling:

```bash
$ python3 bin/create_hugo_pages.py
```

This script will produce *a lot* of files in the `build/content/` subdirectory
(most prominently, one for each paper in the Anthology).

### Step 3: Create bibliography export files for papers

In this step, we create `.bib` files for each paper and proceedings volume in
the Anthology.  This is achieved by calling:

```bash
$ python3 bin/create_bibtex.py
```

The exported files will be written to the `build/data-export/` subdirectory.

For other export formats, we rely on the
[`bibutils`](https://sourceforge.net/p/bibutils/home/Bibutils/) suite by
first converting the generated `.bib` files to MODS XML:

```bash
$ find build/data-export -name '*.bib' -exec bin/bib2xml_wrapper {} \; >/dev/null
```

This creates a corresponding `.xml` file in MODS format for every `.bib` file
generated previously.

### Step 4: Run Hugo

The files that were generated so far are in the `build/` subdirectory, in which
Hugo will be invoked. Before doing this, however, you need to also copy the
content of the `hugo/` subdirectory into `build/` so that all the configuration
files and the page structure is accessible to the engine.

After doing so, the website can be built by simply invoking Hugo from the `build/`
subdirectory.  Optionally, the `--minify` flag can be used to create minified
HTML output:

```bash
$ hugo --minify
```

Generating the website is quite a resource-hungry process, but should not take
longer than a few minutes.  Due to the high memory usage (approx. 18 GB
according to the output of `hugo --stepAnalysis`), it is possible that it will
cause swapping and consequently slow down your system for a while.

The fully generated website will be in `build/anthology/` afterwards.


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
  metadata.  Their format is defined in an RelaxNG schema
  [`schema.rnc`](data/xml/schema.rnc) in the
  same directory.

+ YAML files for SIGs (in [`yaml/sigs/`](data/yaml/sigs)); these contain names,
  URLs, and associated venues for all special interest groups.

+ YAML files that define venues (in [`yaml/venues/`](data/yaml/venues)).
  Each venue has its own yaml file that contains venue specific information
  such as venue acronym, venue full name and venue url.

+ A name variant list ([`name_variants.yaml`](data/yaml/name_variants.yaml)) that
  defines which author names should be treated as identical for purposes of
  generating "author" pages.

The "anthology" module under [`bin/anthology/`](bin/anthology/) is responsible
for parsing and interpreting all these data files.  Some information that is not
explicitly stored in any of these files is *derived automatically* by this
module during Step 1 of building the website.  (For example, if a publication
year is not explicitly given in the XML, it is derived from the volume ID in
[`Paper._infer_year()`](bin/anthology/papers.py).)

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
4.3](https://getbootstrap.com/docs/4.3/).  The final CSS is compiled from
[`hugo/assets/css/main.scss`](hugo/assets/css/main.scss), which defines

1. which Bootstrap components to include,
2. which Bootstrap variables to customize (e.g. colors), and
3. additional style definitions on top of that.


### Adding new years to the Anthology

If a new year is added to the Anthology, make sure the [front page
template](hugo/layouts/index.html) is updated to include this new year.  Make
sure to adjust the variable `$all_years` (and `$border_years`, if needed) and
don't forget to **update the table headers** as well!  (Their `colspan`
attributes need to match the number of years subsumed under the header.)


## Testing & coding style

The following criteria are checked automatically (via Travis CI) and enforced
for all changes pushed to the Anthology:

1. YAML files need to be syntactically well-formed, and XML files need to follow
   the schema definition in [`schema.rnc`](data/xml/schema.rnc).
2. Files should end in exactly one newline, and lines should not have trailing
   whitespace.
3. Python files should have a maximum line length of 90 and follow the
   formatting guidelines defined by the [`black`](https://black.readthedocs.io/)
   tool.
4. Python files need to follow the lint rules covered by the
   [`ruff`](https://github.com/charliermarsh/ruff) tool.  If there's a good
   reason to ignore a rule, [`noqa`
   comments](https://beta.ruff.rs/docs/configuration/#error-suppression) can be
   used on an individual basis.

There are three `make` targets that help you check (and fix) your commits:

+ `make check` will check *all files in the repository.*
+ `make check_commit` will only check files *currently staged for commit.* This
  is best used as a pre-commit hook in order to help you identify problems
  early.
+ `make autofix` works like `check_commit`, except that it will also run the
  [`black`](https://black.readthedocs.io/) code formatter to automatically make
  your Python files style-compliant, and the
  [`ruff`](https://github.com/charliermarsh/ruff) linter to correct those
  linting errors which can be fixed automatically.  This can also be used as a
  pre-commit hook, or run manually when you find that `make check_commit`
  complains about your files.

To easily make any of these targets work as a pre-commit hook, you can create a
symlink to one of the predefined scripts as follows:

+ `ln -s ../../.git-hooks/check_commit .git/hooks/pre-commit` (for check target)
+ `ln -s ../../.git-hooks/autofix .git/hooks/pre-commit` (for autofix target)
