---
Title: Anthology development and API
linktitle: API
subtitle: Information on how to programmatically access Anthology data
date: "2025-09-26"
---

Our source code and data [are available on GitHub](https://github.com/acl-org/acl-anthology/).
Development is coordinated in the [issue tracker](https://github.com/acl-org/acl-anthology/issues/).

### Python API

We have a Python API that defines objects for papers, authors, volumes, and so on.
This is the recommended way to access data about publications in the Anthology.

The API can be installed via pip from [PyPI](https://pypi.org/project/acl-anthology/) or built from source.
Please see our [extensive developer documentation](https://acl-anthology.readthedocs.io/).

Quick access via an interactive Python shell can be achieved by cloning the repository and running
`just python repl` from the repository root directory.

In addition to the documentation, there are many examples of using the module in the scripts our `bin` directory.

### Website software

The ACL Anthology is built from open-source software.
The Anthology website uses the [Hugo](https://gohugo.io/) framework to generate a static website that makes heavy use of the [Bootstrap](https://getbootstrap.com/) library for a modern design. We use [Font Awesome](https://fontawesome.com/) for icon fonts.
[Font Awesome](https://fontawesome.com/) is used as the icon font.

The script [create_hugo_data.py](https://github.com/acl-org/acl-anthology/blob/master/bin/create_hugo_data.py)
generates JSON data structures to build our static site.

### Data organization

All the data in the ACL Anthology is stored under [the data directory](https://github.com/acl-org/acl-anthology/tree/master/data) in our Github repository.
In the `xml` directory are the files that contain all the Anthology metadata, in a format described below.
The `yaml` directory contains further information about authors and venues.

### Authoritative XML format

The Anthology site is generated from an authoritative XML file format containing information about events, volumes, papers, and authors.
This data is stored in [the official repository on Github](https://github.com/acl-org/acl-anthology/tree/master/data/xml).
Here is a simplified fragment of a complete XML file ([P18.xml](https://github.com/acl-org/acl-anthology/blob/master/data/xml/P18.xml)—this file defines the *collection* of volumes from the ACL 2018 main conference).
The full file contains much more information.

```xml
<?xml version="1.0" encoding="UTF-8" ?>
<collection id="P18">
  <volume id="3">
    <meta>
      <booktitle>Proceedings of <fixed-case>ACL</fixed-case> 2018, Student Research Workshop</booktitle>
      <editor><first>Vered</first><last>Shwartz</last></editor>
      <url>P18-3</url>
    </meta>
    <frontmatter>
      <url>P18-3000</url>
      <!-- ... -->
    </frontmatter>
    <paper id="1">
      <title>Towards Opinion Summarization of Customer Reviews</title>
      <author><first>Samuel</first><last>Pecar</last></author>
      <url>P18-3001</url>
      <!-- ... -->
    </paper>
    <paper id="2">
      <title>Sampling Informative Training Data for <fixed-case>RNN</fixed-case> Language Models</title>
      <author><first>Jared</first><last>Fernandez</last></author>
      <author><first>Doug</first><last>Downey</last></author>
      <url>P18-3002</url>
      <!-- ... -->
    </paper>
    <paper id="3">
      <title>Learning-based Composite Metrics for Improved Caption Evaluation</title>
      <author><first>Naeha</first><last>Sharif</last></author>
      <author><first>Lyndon</first><last>White</last></author>
      <author><first>Mohammed</first><last>Bennamoun</last></author>
      <author><first>Syed Afaq</first><last>Ali Shah</last></author>
      <url>P18-3003</url>
      <!-- ... -->
    </paper>
    <!-- ...  -->
  </volume>
</collection>
```

Programmatic access to the data is best achieved through the [Python API](#python-api) rather than through direct parsing of XML files.
