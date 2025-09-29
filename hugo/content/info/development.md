---
Title: Anthology development and API
linktitle: API
subtitle: Information on how to programmatically access Anthology data
date: "2025-09-26"
---

### Data organization

All the data in the ACL Anthology is stored under [the data directory](https://github.com/acl-org/acl-anthology/tree/master/data) in our Github repository.
In the `xml` directory are the files that contain all the Anthology metadata, in a format described below.
The `yaml` directory contains various other important information relating to authors and venues.

### Python API

In addition, we have a Python API that defines objects for papers, authors, volumes, and so on.
This can be installed via pip from [PyPI](https://pypi.org/project/acl-anthology/) or built from source.
For more information on that, please see our [extensive developer documentation](https://acl-anthology.readthedocs.io/).

In addition to the documentation, there are many examples of using the module in the scripts our `bin` directory.
The [create_hugo_yaml.py](https://github.com/acl-org/acl-anthology/blob/master/bin/create_hugo_yaml.py), for example, demonstrates how we generate YAML data structures to build our static site.

### Authoritative XML format

The Anthology site is generated from an authoritative XML file format containing information about volumes, paper titles, and authors.
This data is stored in [the official repository on Github](https://github.com/acl-org/acl-anthology/tree/master/data/xml).
Here is a fragment of a complete XML file ([P18.xml](https://github.com/acl-org/acl-anthology/blob/master/data/xml/P18.xml)), to give you the idea.
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

Our scripts use the [lxml.de](http://lxml.de) library to parse the XML.
You can see examples of parsing and accessing the XML directly in [add_revision.py](https://github.com/acl-org/acl-anthology/blob/master/bin/add_revision.py) and [ingest.py](https://github.com/acl-org/acl-anthology/blob/master/bin/ingest.py).
