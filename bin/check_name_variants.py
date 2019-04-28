import yaml, yamlfix
import sys
import lxml.etree as etree
import logging

person_fields = {'canonical', 'variants', 'comment'}
name_fields = {'first', 'last', 'papers'}

def text(node):
    """Extract text from an XML node."""
    if node is None:
        return ''
    if 'complete' in node.attrib:
        s = node.attrib['complete']
    else:
        s = ''.join(node.itertext())
    return ' '.join(s.split())

def name(d):
    return (d['first'], d['last'])

if len(sys.argv) > 2:
    names = set()
    for xmlfilename in sys.argv[2:]:
        try:
            tree = etree.parse(xmlfilename)
        except:
            logging.error("couldn't parse {}".format(xmlfilename))
            raise
        for paper in tree.getroot().findall('paper'):
            for person in paper.xpath('./author|./editor'):
                first = text(person.find('first'))
                last = text(person.find('last'))
                names.add((first,last))
else:
    names = None

doc = yaml.load(open(sys.argv[1]))

assert isinstance(doc, list)
for person in doc:
    assert isinstance(person, dict), person
    assert set(person.keys()).issubset(person_fields), person
    assert 'canonical' in person, person
    assert isinstance(person['canonical'], dict), person
    assert set(person['canonical']).issubset(name_fields), person
    if names is not None and name(person['canonical']) not in names:
        logging.warning('unused name: {}'.format(person['canonical']))
    dupes = {name(person['canonical'])}
    assert 'variants' in person, person
    assert isinstance(person['variants'], list), person
    for variant in person['variants']:
        assert set(variant).issubset(name_fields), person
        if names is not None and name(variant) not in names:
            logging.warning('unused name: {}'.format(variant))
        assert name(variant) not in dupes, variant
        dupes.add(name(variant))
        
print(yaml.dump(doc, allow_unicode=True))
