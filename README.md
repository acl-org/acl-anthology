# ACL Anthology

[![ACL Anthology Website](https://img.shields.io/badge/ACL_Anthology_Website-grey.svg?style=flat&logo=data:image/svg+xml;base64,PD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0iVVRGLTgiIHN0YW5kYWxvbmU9Im5vIj8+CjwhLS0gQ3JlYXRlZCB3aXRoIElua3NjYXBlIChodHRwOi8vd3d3Lmlua3NjYXBlLm9yZy8pIC0tPgo8c3ZnCiAgIHhtbG5zOnN2Zz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciCiAgIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyIKICAgdmVyc2lvbj0iMS4wIgogICB3aWR0aD0iNjgiCiAgIGhlaWdodD0iNjgiCiAgIGlkPSJzdmcyIj4KICA8ZGVmcwogICAgIGlkPSJkZWZzNCIgLz4KICA8cGF0aAogICAgIGQ9Ik0gNDEuOTc3NTUzLC0yLjg0MjE3MDllLTAxNCBDIDQxLjk3NzU1MywxLjc2MTc4IDQxLjk3NzU1MywxLjQ0MjExIDQxLjk3NzU1MywzLjAxNTggTCA3LjQ4NjkwNTQsMy4wMTU4IEwgMCwzLjAxNTggTCAwLDEwLjUwMDc5IEwgMCwzOC40Nzg2NyBMIDAsNDYgTCA3LjQ4NjkwNTQsNDYgTCA0OS41MDA4MDIsNDYgTCA1Ni45ODc3MDgsNDYgTCA2OCw0NiBMIDY4LDMwLjk5MzY4IEwgNTYuOTg3NzA4LDMwLjk5MzY4IEwgNTYuOTg3NzA4LDEwLjUwMDc5IEwgNTYuOTg3NzA4LDMuMDE1OCBDIDU2Ljk4NzcwOCwxLjQ0MjExIDU2Ljk4NzcwOCwxLjc2MTc4IDU2Ljk4NzcwOCwtMi44NDIxNzA5ZS0wMTQgTCA0MS45Nzc1NTMsLTIuODQyMTcwOWUtMDE0IHogTSAxNS4wMTAxNTUsMTcuOTg1NzggTCA0MS45Nzc1NTMsMTcuOTg1NzggTCA0MS45Nzc1NTMsMzAuOTkzNjggTCAxNS4wMTAxNTUsMzAuOTkzNjggTCAxNS4wMTAxNTUsMTcuOTg1NzggeiAiCiAgICAgc3R5bGU9ImZpbGw6I2VkMWMyNDtmaWxsLW9wYWNpdHk6MTtmaWxsLXJ1bGU6ZXZlbm9kZDtzdHJva2U6bm9uZTtzdHJva2Utd2lkdGg6MTIuODk1NDExNDk7c3Ryb2tlLWxpbmVjYXA6YnV0dDtzdHJva2UtbGluZWpvaW46bWl0ZXI7c3Ryb2tlLW1pdGVybGltaXQ6NDtzdHJva2UtZGFzaGFycmF5Om5vbmU7c3Ryb2tlLWRhc2hvZmZzZXQ6MDtzdHJva2Utb3BhY2l0eToxIgogICAgIHRyYW5zZm9ybT0idHJhbnNsYXRlKDAsIDExKSIKICAgICBpZD0icmVjdDIxNzgiIC8+Cjwvc3ZnPgo=)](https://aclanthology.org)
[![GitHub contributors](https://img.shields.io/github/contributors/acl-org/acl-anthology)](https://github.com/acl-org/acl-anthology/graphs/contributors)
[![Good first project issues](https://img.shields.io/github/issues/acl-org/acl-anthology/good%20first%20project)](https://github.com/acl-org/acl-anthology/issues?q=is%3Aissue+is%3Aopen+sort%3Aupdated-desc+label%3A%22good+first+project%22)
[![License](https://img.shields.io/github/license/acl-org/acl-anthology)](LICENSE)
[![acl-anthology-py on PyPI](https://img.shields.io/pypi/v/acl-anthology-py?logo=python&label=acl-anthology-py&labelColor=lightgray&color=3776AB)](https://pypi.org/project/acl-anthology-py/)

This repository contains:

- [**Metadata for all papers, authors, and venues**](data/) on the [ACL Anthology website](https://aclanthology.org/).
- **Code and instructions** for generating the website.
- [**A Python package for accessing the metadata**](python/), also available on PyPI.

The official home of this repository is <https://github.com/acl-org/acl-anthology>.

## Using the acl-anthology-py Python package

Please see the separate [README for the Python package](python/README.md) for detailed information.

## Generating the Anthology website

These are basic instructions on generating the ACL Anthology website as seen on <https://aclanthology.org/>.

### Prerequisites

To build the Anthology website, you will need:

+ **Python 3.8** or higher
+ Python packages listed in `bin/requirements.txt`; to install, run `pip -r bin/requirements.txt`
+ [**Hugo 0.58.3**](https://gohugo.io) or higher (can be [downloaded directly from
  their repo](https://github.com/gohugoio/hugo/releases); the ***extended version*** is required!)
+ [**bibutils**](https://sourceforge.net/p/bibutils/home/Bibutils/) for creating
  non-BibTeX citation formats (not strictly required to build the website, but
  without them you need to invoke the build steps manually as laid out in the
  [detailed README](README_detailed.md))
+ *optional*: If you install `libyaml-dev` and `Cython` before running `make`
   the first time, the libyaml C library will be used instead of a python
   implementation, speeding up the build.

### Building and deployment with GitHub

There is a GitHub actions action performing deployment directly from GitHub.  To use this, you need to
define this variable in your repository settings (web interface: settings -> secrets):

+ `PUBLISH_SSH_KEY`: the secret key in standard pem format for authentication (without a passphrase)

GitHub will then automatically build and deploy the current master whenever the master branch changes.
This is done via the `upload` target in the Makefile.

### Cloning

Clone the Anthology repo to your local machine:

```bash
$ git clone https://github.com/acl-org/acl-anthology
```

### Generating

Provided you have correctly installed all requirements, building the website
should be as simple running `make` from the directory to which
you cloned the repo.

The fully generated website will be in `build/anthology` afterwards.  If any errors
occur during this step, you can consult the [detailed
README](README_detailed.md) for more information on the individual steps
performed to build the site.  You can see the resulting website by launching
a local webserver with `make serve`, which will serve it at http://localhost:8000.

Note that building the website is quite a resource-intensive process;
particularly the last step, invoking Hugo, uses about 18~GB of system memory.
Building the anthology takes about 10 minutes on a laptop with an SSD.

(**Note:** This does *not* mean you need this amount of RAM in your system; in
fact, the website builds fine on a laptop with 8 GB of RAM.  The system might
temporarily slow down due to swapping, however.  The figure of approx. 18 GB is
the maximum RAM usage reported when running `hugo --minify --stepAnalysis`.)

The anthology can be viewed locally by running `hugo server` in the
`hugo/` directory.  Note that it rebuilds the site and therefore takes
about a minute to start.


## Hosting a mirror of the ACL anthology

First, creating a mirror is slow and stresses the ACL Anthology
infrastructure because on initial setup you have to download every
single file of the anthology from the official webserver.  This can
take up to 8 hours no matter how fast *your* connection is.  So please
don't play around with this just for fun.

If you want to host a mirror, you have to set two environment variables:
 - `ANTHOLOGY_PREFIX` the http prefix your mirror will be reachable under
   e.g. https://example.com/my-awesome-mirror or http://aclanthology.lst.uni-saarland.de
   (Notice that there is no slash at the end!)
 - `ANTHOLOGYFILES` the directory under which papers, attachments etc.
   will reside on your webserver.  This directory needs to be readable
   by your webserver (obviously) but should not be a subdirectory
   of the anthology mirror directory.

With these variables set, you run `make` to create the pages and `make
mirror` to mirror all additional files into the build/anthology-files
directory.  If you created a mirror before already, it will only
download the missing files.

If you want to mirror the papers but not all attachments, you can run
`make mirror-no-attachments` instead.

You then rsync the `build/website/` directory to your webserver or, if
you serve the mirror in a subdirectory `FOO`, you mirror
`build/website/FOO`.  The `build/anthology-files` directory needs to
be rsync-ed to the `ANTHOLOGYFILES` directory of your webserver.

As you probably want to keep the mirror up to date, you can modify the
shell script `bin/acl-mirror-cronjob.sh` to your needs.

You will need this software on the server
 - rsync
 - git
 - python3
 - hugo > 0.58
 - python3-venv

If you want the build process to be fast, install `cython3` and
`libyaml-dev` (see above).

Note that generating the anthology takes quite a bit of RAM, so make
sure it is available on your machine.

## Contributing

If you'd like to contribute to the ACL Anthology, please take a look at:

- our [Github issues page](https://github.com/acl-org/acl-anthology/issues)
- the [detailed README](README_detailed.md) which contains more in-depth information about generating and modifying the website.

## History

This repo was originally wing-nus/acl and has been transferred over to acl-org as of 5 June 2017.

## License

The code for building the ACL Anthology is distributed under the [Apache License, v2.0](https://www.apache.org/licenses/LICENSE-2.0).
