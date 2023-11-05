# Types of Metadata

Items in the Anthology can have various kinds of metadata, which are listed and
described in detail in the API documentation for their respective object;
e.g. [papers][acl_anthology.collections.paper.Paper],
[volumes][acl_anthology.collections.volume.Volume],
[events][acl_anthology.collections.event.Event], [SIGs][acl_anthology.sigs.SIG],
[venues][acl_anthology.venues.Venue], etc.

## Plain metadata fields

Some metadata fields are simply strings or lists of strings; for example:

```python
paper = anthology.get("2022.acl-long.220")
paper.bibkey           # is 'kitaev-etal-2022-learned'
paper.doi              # is '10.18653/v1/2022.acl-long.220'
paper.year             # is '2022'
paper.awards           # is ['Best Paper']
```

However, many of them are optional, and can be `None` or empty.

```python
paper.attachments      # is {}
paper.language         # is None
```

## Markup text

Two of the most common field types, **titles** and **abstracts**, can contain
_markup text_.  They support a limited set of markup tags to denote, e.g., bold
and italics, TeX math expressions, URLs, protected case (i.e. marking capitals
that should never be lowercased in bibliographic references), and potentially
more in the future.

This means that such metadata fields don't contain strings, but rather
[`MarkupText`][acl_anthology.text.MarkupText] instances:

```pycon
>>> paper = anthology.get("2022.acl-short.58")
>>> paper.title
MarkupText('S<span class="tex-math"><sup>4</sup></span>-Tuning: A Simple Cross-lingual Sub-network Tuning Method')
```

To work with these as Unicode strings, you need to explicitly convert them:
```pycon
>>> str(paper.title)
'S4-Tuning: A Simple Cross-lingual Sub-network Tuning Method'
```

Alternatively, they can be converted into HTML or LaTeX representations:

```pycon
>>> paper.title.as_html()
'S<span class="tex-math"><sup>4</sup></span>-Tuning: A Simple Cross-lingual Sub-network Tuning Method'
>>> paper.title.as_latex()
'S$^4$-Tuning: A Simple Cross-lingual Sub-network Tuning Method'
```

## File references

Some metadata fields refer to **files**, the most common of which is the **PDF
file** for a paper:

```pycon
>>> paper = anthology.get("2021.eacl-main.89")
>>> paper.pdf
PDFReference(name='2021.eacl-main.89', checksum='27663bea')
```

These are always classes that inherit from
[`FileReference`][acl_anthology.files.FileReference]. As you can see above, they
usually[^1] give only the base filename.  You can, however, easily obtain the
full URL for these:

```pycon
>>> paper.pdf.url
'https://aclanthology.org/2021.eacl-main.89.pdf'
```

Some other places where you might encounter file references are **attachments**
or **event links**:

```pycon
>>> paper.attachments
{
  'Software': AttachmentReference(name='2021.eacl-main.89.Software.zip', checksum='ca8afe3f'),
  'Dataset': AttachmentReference(name='2021.eacl-main.89.Dataset.txt', checksum='07778fe5')
}
>>> anthology.get_event("acl-2022").links
{
  'website': AttachmentReference(name='https://2022.aclweb.org', checksum=None),
  'handbook': AttachmentReference(name='2022.acl.handbook.pdf', checksum=None)
}
```

Most file references also include the _checksum_ field, which is a [CRC32
checksum](https://docs.python.org/3/library/zlib.html#zlib.crc32) of the
respective file that can be used to verify if it was downloaded correctly.

[^1]: For all materials hosted on the ACL Anthology web server.
