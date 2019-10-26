---
Title: How do I link to publications in the ACL Anthology?
weight: 1
---

Every paper in the Anthology is assigned an Anthology ID.
Prior to 2020, this identifier took the form `CYY-VPPP` or `CYY-VVPP`, where `C` identifies a collection, `YY` a two-digit year, `V` a volume, and `P` a paper ID.
The "W" collection identifier reserves two positions for the volume and two for the paper ID, whereas all other collections reserve one for the volume and three for the paper ID.
The **canonical URL** of an Anthology paper is given by appending this identifier to the Anthology prefix of <https://www.aclweb.org/anthology/>; e.g., <https://www.aclweb.org/anthology/E91-1001>.
When accessed via web browser, this page returns the paper's landing page, which includes (among other things) a link to the PDF.

Many papers in the Anthology also have Digital Object Identifiers (DOIs). 
Both the DOIs and the canonical Anthology URLs embed the 8-character ACL Anthology Identifier.
When available, DOI URLs will redirect to the Anthology canonical URL, and will be listed on that page.

Variations of the canonical URL can be used to access the PDF and citation format files directly:

- Append `.pdf` to get the PDF, e.g., <https://www.aclweb.org/anthology/E91-1001.pdf>
- Append `.bib` to retrieve the BibTeX file, e.g., <https://www.aclweb.org/anthology/E91-1001.bib>
- Append `.xml` to get the [MODS-formatted](http://www.loc.gov/standards/mods/) XML file, e.g., <https://www.aclweb.org/anthology/E91-1001.xml>

and so on.
