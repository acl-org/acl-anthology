# ACL Anthology

These are basic instructions on generating the ACL Anthology website as seen on <https://aclanthology.org/>.
The official home of this repository is <https://github.com/acl-org/acl-anthology>.

## Generating the Anthology

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

First, creating a mirror is slow and stresses the ACL anthology
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
