import yaml, yamlfix
import sys
import anthology
import logging
import os.path

scriptdir = os.path.dirname(os.path.abspath(__file__))
datadir = os.path.join(scriptdir, '..', 'data')

anth = anthology.Anthology(importdir=datadir)

variants = yaml.safe_load(open(os.path.join(datadir, 'yaml', 'name_variants.yaml')))

newvariants = []
for d in variants:
    name = anthology.people.PersonName.from_dict(d['canonical'])
    if len(anth.people.name_to_papers[name][False]) == 0:
        logging.info("unused canonical name: {}".format(name))
    for var in list(d.get('variants', [])):
        name = anthology.people.PersonName.from_dict(var)
        if len(anth.people.name_to_papers[name][False]) == 0:
            logging.info("pruning unused variant: {}".format(name))
            d['variants'].remove(var)
    if 'variants' in d and len(d['variants']) == 0:
        del d['variants']
    if list(d.keys()) == ['canonical']:
        continue
    newvariants.append(d)

newvariants.sort(key=lambda v: (v['canonical']['last'], v['canonical']['first']))

sys.stdout.write(yaml.dump(newvariants, allow_unicode=True, default_flow_style=None))

