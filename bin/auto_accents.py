"""
Try to automatically restore accents in author names by downloading and scraping the PDFs.
Reads and writes Anthology XML files.
"""

import tika.parser
import requests
import sys
import lxml.etree as etree
import re
import unicodedata
import os.path
import yaml, yamlfix
import copy

def guess_url(paper):
    url = paper.find('url') is not None and paper.find('url').text
    if not url: url = paper.find('href') and paper.find('href').text
    if not url: url = paper.attrib.get('href', None)
    if not url:
        volume = paper.getparent()
        url = "http://www.aclweb.org/anthology/{}-{}".format(volume.attrib['id'], paper.attrib['id'])
    return url

def remove_accents(s):
    s = unicodedata.normalize('NFKD', s)
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return s.lower()

def scrape_authors(url):
    logger.info("getting {}".format(url))
    try:
        r = requests.get(url)
        if not r:
            logger.error("could not download PDF")
            return None
        raw = tika.parser.from_buffer(r.content)
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
        if n > 50: break

        # In PDF, sometimes i with accent is dotless i as in TeX,
        # but NFKC doesn't get this
        line = list(line)
        for i in range(len(line)-1):
            # bug: we should only be looking for accents above, not
            # below
            if line[i] == 'ı' and unicodedata.category(line[i+1]) == 'Mn':
                line[i] = 'i'
        line = ''.join(line)

        # Remove email addresses, which are often same as names.
        # There can be spaces inside the curly braces.
        line = re.sub(r'(\{.*?\}|\S+)@\S+', '', line)

        line = unicodedata.normalize('NFKC', line)
        logger.debug('> '+line)
        for word in line.split():
            while len(word) > 0 and not (word[-1].isalpha() or
                                         word[-1] in '.’'):
                word = word[:-1]
            rword = remove_accents(word)
            if rword in index and index[rword] != word:
                logging.warning("word '{}' appears twice with different accents".format(rword))
                continue
            index[rword] = word
    #print(index)
    return index

def change(index, word):
    rword = remove_accents(word)
    if rword in index:
        newword = index[rword]
        if newword != word:
            logger.info("changing: {} -> {}".format(word, newword))
        return newword
    else:
        logger.warning("word {} in XML but not in PDF".format(rword))
        return word

if __name__ == "__main__":
    import argparse
    import logging
    
    # Set up logging
    logger = logging.getLogger("auto_accents")
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(levelname)s:%(location)s %(message)s'))
    location = ""
    def filter(r):
        r.location = location
        return True
    handler.addFilter(filter)
    #logger.setLevel(logging.INFO)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    logger.propagate = False
    
    ap = argparse.ArgumentParser(description='Try to automatically restore accents in author names.')
    ap.add_argument('infile', help="input XML file")
    ap.add_argument('outfile', help="output XML file")
    args = ap.parse_args()

    scriptdir = os.path.dirname(os.path.abspath(__file__))

    variants = yaml.load(open(os.path.join(scriptdir, '..', 'data', 'yaml', 'name_variants.yaml')))
    variant_index = set()
    for person in variants:
        for name in [person['canonical']] + person.get('variants', []):
            variant_index.add((name['first'], name['last']))

    tree = etree.parse(args.infile)
    volume = tree.getroot()
    if not volume.tail: volume.tail = "\n"
    for paper in volume.findall('paper'):
        paperid = '{}-{}'.format(volume.attrib['id'], paper.attrib['id'])
        location = paperid + ":"

        url = guess_url(paper)
        index = scrape_authors(url)
        if index is None: continue
            
        for xauthornode in paper.xpath('./author|./editor'):
            xfirstnode = xauthornode.find('first')
            xlastnode = xauthornode.find('last')
            assert(len(xfirstnode) == len(xlastnode) == 0)

            xfirst = (xfirstnode.text or "").strip()
            xlast = xlastnode.text.strip()
            location = '{} {} {} {}:'.format(paperid, xauthornode.tag, xfirst, xlast)

            newfirst = ' '.join(change(index, word) for word in xfirst.split())
            newlast = ' '.join(change(index, word) for word in xlast.split())
            if (xfirst, xlast) in variant_index and (newfirst, newlast) not in variant_index:
                logging.warning("add new name '{} {}' to name_variants.yaml".format(newfirst, newlast))
            xfirstnode.text = newfirst
            xlastnode.text = newlast
                    
    tree.write(args.outfile, xml_declaration=True, encoding='UTF-8')
