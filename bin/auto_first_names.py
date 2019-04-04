"""
Try to automatically fill in author first names by downloading and scraping the PDFs.
Reads and writes Anthology XML files.

Bugs:

- If two authors on the same paper have same last name, one of them will get the wrong 
  first name. This could be remedied somewhat by using the first initial as a clue. 
  Otherwise, we should check for duplicate names.
- If name is broken across two lines, there is no first name.
- Strip punctuation from XML names too
- Strip "and" from beginning
"""

import tika.parser
import requests
import sys
import lxml.etree as etree
import re
import unicodedata
import os.path

if len(sys.argv) != 3:
    sys.exit("usage: auto_first_names.py <input-xml> <output-xml>")

tree = etree.parse(sys.argv[1])
for paper in tree.findall('paper'):
    print("paper", paper.attrib['id'])
    url = paper.find('url') and paper.find('url').text
    if url is None: url = paper.find('href') and paper.find('href').text
    if url is None: url = paper.attrib.get('href', None)
    if url is None:
        filename = os.path.basename(sys.argv[1])
        assert filename.endswith('.xml')
        filename = filename[:-4]
        url = "http://www.aclweb.org/anthology/{}-{}".format(filename, paper.attrib['id'])
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
        line = unicodedata.normalize('NFKC', line)
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

    allnames = set()
    for xauthornode in paper.findall('author'):
        xfirstnode = xauthornode.find('first')
        xlastnode = xauthornode.find('last')
        assert(len(xfirstnode) == len(xlastnode) == 0)
        
        xfirst = (xfirstnode.text or "").strip()
        xlast = xlastnode.text.strip()
        xname = '{} {}'.format(xfirst, xlast) # just used for logging
        
        if xlast.lower() not in index:
            print("warning: {} not found; skipping".format(xname))
            continue
        
        pname = index[xlast.lower()]
        i = pname.lower().find(xlast.lower())
        newfirst = pname[:i].strip()
        afterlast = pname[i+len(xlast):].strip()
        if afterlast:
            print("warning: {}: trailing string after last name: {}".format(xname, afterlast))
        if (newfirst, xlast) in allnames:
            print("warning: {}: duplicate new first name: {}".format(xname, newfirst))
        allnames.add((newfirst, xlast))
        print("{} {} -> {} {}".format(xfirst, xlast, newfirst, xlast))
        xfirstnode.text = newfirst

    print()
tree.write(sys.argv[2], xml_declaration=True, encoding='UTF-8', with_tail=True)
