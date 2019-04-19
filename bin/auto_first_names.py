"""
Try to automatically fill in author first names by downloading and scraping the PDFs, or from name_variants.yaml.
Reads and writes Anthology XML files.

Bugs:

- If two authors on the same paper have same last name, one of them will get the wrong 
  first name. This could be remedied somewhat by using the first initial as a clue. 
- If name is broken across two lines, there is no first name.
- Strip punctuation from XML names too
"""

import tika.parser
import requests
import sys
import lxml.etree as etree
import re
import unicodedata
import os.path
import yaml

initial_re = re.compile(r'([A-Z])\b\.?\s*')
def find_initials(s):
    # Doesn't recognize "JRR" as initials; how would we distinguish
    # from a name in all-caps?
    s = s.lstrip()
    initials = []
    i = 0
    while i < len(s):
        m = initial_re.match(s, i)
        if not m: return None
        initials.append(m.group(1))
        i = m.end()
    return ''.join(initials)

def guess_url(paper):
    url = paper.find('url') is not None and paper.find('url').text
    if not url: url = paper.find('href') and paper.find('href').text
    if not url: url = paper.attrib.get('href', None)
    if not url:
        volume = paper.getparent()
        url = "http://www.aclweb.org/anthology/{}-{}".format(volume.attrib['id'], paper.attrib['id'])
    return url

def scrape_authors(url):
    logger.info("getting {}".format(url))
    try:
        req = requests.get(url)
        raw = tika.parser.from_buffer(req.content)
        text = raw['content']
    except KeyboardInterrupt:
        raise
    except Exception as e:
        logger.error(str(e))
        return {}
    
    index = {}
    n = 0
    for line in text.splitlines():
        nospace = ''.join(line.split())
        if nospace == 'Abstract': break
        if nospace == '': continue

        n += 1
        if n > 20: break

        line = unicodedata.normalize('NFKC', line)
        logger.info('> '+line)
        names = re.split(r',\s*|\band\s+|,\s*and\s+|&', line)
        for name in names:
            # strip leading and trailing numbers, punctuation, symbols, whitespace
            # bugs: can a name end in an apostrophe?
            while len(name) > 0 and unicodedata.category(name[0])[0] in "NPSZ":
                name = name[1:]
            while len(name) > 0 and unicodedata.category(name[-1])[0] in "NPSZ":
                name = name[:-1]
            parts = name.split()
            for i in range(1, len(parts)-1):
                first = ' '.join(parts[:i])
                last = ' '.join(parts[i:])
                flast = first[0], last
                if flast not in index: # ignore subsequent mentions, which may be from text
                    index[flast] = (first, last)
    return index

if __name__ == "__main__":
    import argparse
    import logging
    
    # Set up logging
    logger = logging.getLogger("auto_first_names")
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(levelname)s:%(location)s %(message)s'))
    location = ""
    def filter(r):
        r.location = location
        return True
    handler.addFilter(filter)
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    logger.propagate = False
    
    ap = argparse.ArgumentParser(description='Try to automatically expand first initials into first names.')
    ap.add_argument('infile', help="input XML file")
    ap.add_argument('outfile', help="output XML file")
    ap.add_argument('-s', '--scrape', action="store_true", help="try to scrape first names from PDF")
    ap.add_argument('-y', '--variants', help="try to get first names from name_variants.yaml")
    args = ap.parse_args()

    scriptdir = os.path.dirname(os.path.abspath(__file__))

    if args.variants:
        variants = {}
        for person in yaml.load(open(args.variants)):
            for name in person['variants']:
                initials = find_initials(name['first'])
                if initials:
                    flast = (''.join(initials), name['last'])
                    canonical = person['canonical']['first'], person['canonical']['last'] 
                    if flast in variants and variants[flast] != canonical:
                        logging.warning("ambiguous variant: {} -> {} and {}".format(flast, variants[flast], canonical))
                    variants[flast] = canonical
                    # to do: sometimes the canonical name isn't the best way to expand an initial
        
    tree = etree.parse(args.infile)
    volume = tree.getroot()
    for paper in volume.findall('paper'):
        paperid = '{}-{}'.format(volume.attrib['id'], paper.attrib['id'])
        location = paperid + ":"

        # Skip if there are no first initials
        for xauthornode in paper.xpath('./author|./editor'):
            xfirstnode = xauthornode.find('first')
            if xfirstnode is None: continue
            assert(len(xfirstnode) == 0)
            xfirst = (xfirstnode.text or "").strip()
            if find_initials(xfirst):
                break
        else:
            continue

        if args.scrape:
            url = guess_url(paper)
            index = scrape_authors(url)
            
        allnames = set()
        for xauthornode in paper.xpath('./author|./editor'):
            xfirstnode = xauthornode.find('first')
            xlastnode = xauthornode.find('last')
            assert(len(xfirstnode) == len(xlastnode) == 0)

            xfirst = (xfirstnode.text or "").strip()
            xinitials = find_initials(xfirst)
            if not xinitials:
                continue
            xlast = xlastnode.text.strip()
            location = '{} {} {} {}:'.format(paperid, xauthornode.tag, xfirst, xlast)

            if args.scrape:
                # currently broken
                if xlast.lower() not in index:
                    logger.warning("not found; skipping")
                    continue

                pname = index[xlast.lower()]
                i = pname.lower().find(xlast.lower())
                newfirst = pname[:i].strip()
                afterlast = pname[i+len(xlast):].strip()
                if afterlast:
                    logger.warning("trailing string after last name: {}".format(afterlast))
                if (newfirst, xlast) in allnames:
                    logger.warning("duplicate new first name (this usually requires manual correction): {}".format(newfirst))
                if newfirst == "":
                    logger.warning("empty first name; skipping")
                    continue
                allnames.add((newfirst, xlast))
                if newfirst != xfirst:
                    logger.info("changing: {} {} -> {} {}".format(xfirst, xlast, newfirst, xlast))
                    xfirstnode.text = newfirst

            if args.variants:
                if 'complete' in xfirstnode.attrib:
                    logger.debug('already has completion: {}'.format(xfirstnode.attrib['complete']))
                    continue
                xflast = (xinitials, xlast)
                if xflast in variants:
                    newfirst, newlast = variants[xflast]
                    if newlast == xlast and newfirst != xfirst:
                        logger.info("adding completion: {}".format(newfirst))
                        xfirstnode.attrib['complete'] = newfirst
                        continue
                logger.info("couldn't find among name variants")
                    
    tree.write(args.outfile, xml_declaration=True, encoding='UTF-8', with_tail=True)
