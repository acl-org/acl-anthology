# ACL Anthology

(This repo was originally wing-nus/acl and has been transferred over to acl-org
as of 5 Jun 2017.  Please update accordingly.)

These are basic instructions on generating the ACL Anthology website as seen on
<https://aclweb.org/anthology/>.


## Generating the Anthology

### Prerequisites

To build the Anthology website, you will need:

+ **Python 3.7** or higher, along with the packages listed in
  [bin/requirements.txt](bin/requirements.txt)
  + *Note:* [Installing the PyYAML package with C
    bindings](http://rmcgibbo.github.io/blog/2013/05/23/faster-yaml-parsing-with-libyaml/)
    will speed up the generation process.
+ [**Hugo 0.54**](https://gohugo.io) or higher (can be [downloaded directly from
  their repo](https://github.com/gohugoio/hugo/releases); the ***extended version*** is required!)
+ [**bibutils**](https://sourceforge.net/p/bibutils/home/Bibutils/) for creating
  non-BibTeX citation formats (not strictly required to build the website, but
  without them you need to invoke the build steps manually as laid out in the
  [detailed README](README_detailed.md))

### Cloning

Clone the Anthology repo to your local machine:

```bash
$ git clone https://github.com/acl-org/acl-anthology
```

### Generating

Provided you have correctly installed all requirements, building the website
should be as simple as calling the following command from the directory to which
you cloned the repo:

```bash
$ bin/build_hugo
```

The fully generated website will be in `hugo/public/` afterwards.  If any errors
occur during this step, you can consult the [detailed
README](README_detailed.md) for more information on the individual steps
performed to build the site.

Note that building the website is quite a resource-intensive process;
particularly the last step, invoking Hugo, uses about 18~GB of system memory.

(**Note:** This does *not* mean you need this amount of RAM in your system; in
fact, the website builds fine on a laptop with 8 GB of RAM.  The system might
temporarily slow down due to swapping, however.  The figure of approx. 18 GB is
the maximum RAM usage reported when running `hugo --minify --stepAnalysis`.)


## Contributing

If you'd like to contribute to the ACL Anthology, please take a look at our
[information on volunteering](https://aclanthology.info/volunteer) and the
[detailed README](README_detailed.md) containing more in-depth information about
generating and modifying the website.


## License

Materials prior to 2016 here are licensed under the [Creative Commons
Attribution-NonCommercial-ShareAlike 3.0 International
License](https://creativecommons.org/licenses/by-nc-sa/3.0/).  Permission is
granted to make copies for the purposes of teaching and research.  Materials
published in or after 2016 are licensed on a [Creative Commons Attribution 4.0
License](https://creativecommons.org/licenses/by/4.0/).

Matt Post (Editor, 2019-) / Min-Yen Kan (Editor, 2008-2018) / Steven Bird (Editor, 2001-2007)

Developer team: Linh Hien Ng (linhhienng at gmail dot com), Duong Ho Tuan zamakkat at gmail dot com)
