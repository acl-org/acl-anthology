# Workaround for bug in PyYAML

import yaml
import re

for name in ["Dumper", "SafeDumper", "CDumper", "CSafeDumper"]:
    try:
        Dumper = yaml.__dict__[name]
    except KeyError:
        continue
    Dumper.add_implicit_resolver("tag:yaml.org,2002:bool", re.compile("^[YNyn]$"), "YNyn")
