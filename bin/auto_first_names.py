"""
Try to automatically fill in author first names by downloading and scraping the PDFs.
Reads and writes Anthology XML files.

Bugs:

- If two authors on the same paper have same last name, one of them will get the wrong 
  first name. This could be remedied somewhat by using the first initial as a clue. 
  Otherwise, we should check for duplicate names.
- If name is broken across two lines, there is no first name.
- Strip whitespace, punct from XML names too
- Strip "and" from beginning
- NFKC normalization
"""

import tika.parser
import requests
import sys
import lxml.etree as etree
import re
import unicodedata

if len(sys.argv) != 3:
    sys.exit("usage: auto_first_names.py <input-xml> <output-xml>")

tree = etree.parse(sys.argv[1])
for paper in tree.findall('paper'):
    print("paper", paper.attrib['id'])
    url = paper.find('url') and paper.find('url').text
    if url is None: url = paper.find('href') and paper.find('href').text
    if url is None: url = paper.attrib.get('href', None)
    if url is None:
        print('no url found; skipping')
        print()
        continue

    print("getting", url)
    try:
        req = requests.get(url)
        raw = tika.parser.from_buffer(req.content)
        text = [line for line in raw['content'].splitlines() if line.strip() != ""]
    except KeyboardInterrupt:
        raise
    except Exception as e:
        print("error: {}".format(e))
        continue

    index = {}
    for line in text[:20]:
        if line.strip() == 'Abstract': break
        print('> '+line)
        names = re.split(r',\s*|\s+and\s+|,\s*and\s+|&', line)
        for name in names:
            # strip leading and trailing numbers, punctuation, symbols, whitespace
            # bugs: can a name end in an apostrophe?
            while len(name) > 0 and unicodedata.category(name[0])[0] in "NPSZ":
                name = name[1:]
            while len(name) > 0 and unicodedata.category(name[-1])[0] in "NPSZ":
                name = name[:-1]
            for part in name.split():
                if part not in index: # ignore subsequent mentions, which may be from text
                    index[part.lower()] = name

    for xauthor in paper.findall('author'):
        xfirst = xauthor.find('first')
        xlast = xauthor.find('last')
        xnametext = '{} {}'.format(xfirst.text, xlast.text) # just used for logging
        assert(len(xfirst) == len(xlast) == 0)
        if xlast.text.lower() not in index:
            print("warning: {} not found; skipping".format(xnametext))
            continue
        pname = index[xlast.text.lower()]
        i = pname.lower().find(xlast.text.lower())
        newfirst = pname[:i].strip()
        afterlast = pname[i+len(xlast.text):].strip()
        if afterlast:
            print("warning: {}: trailing string after last name: {}".format(xnametext, afterlast))
        print("{} {} -> {} {}".format(xfirst.text, xlast.text, newfirst, xlast.text))
        xfirst.text = newfirst

    print()
tree.write(sys.argv[2], xml_declaration=True, encoding='UTF-8', with_tail=True)
