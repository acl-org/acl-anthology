# ACL Anthology

(This repo was originally wing-nus/acl and has been transferred over to acl-org
as of 5 Jun 2017.  Please update accordingly.)

:warning: **This branch contains the static rewrite of the Anthology.  It is
*WORK IN PROGRESS* and still missing substantial functionality.** :warning:

These are basic instructions on generating the ACL Anthology website as seen on
<https://aclanthology.info>.


## Generating the Anthology

### Prerequisites

To build the Anthology website, you will need:

+ Python 3.5 or higher, along with the packages listed in
  [bin/requirements.txt](bin/requirements.txt)
  + *Note:* [Installing the PyYAML package with C
    bindings](http://rmcgibbo.github.io/blog/2013/05/23/faster-yaml-parsing-with-libyaml/)
    will speed up the generation process.
+ [Hugo 0.53](https://gohugo.io) or higher (can be [downloaded directly from
  their repo](https://github.com/gohugoio/hugo/releases))


### Cloning

Browse to your designated folder and clone the Anthology repo using this git
command (or with a git GUI tool). The process should take a while since the
repository is quite big (about 150MB):

```bash
$ git clone https://github.com/acl-org/acl-anthology
```


### Generating

TODO



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
