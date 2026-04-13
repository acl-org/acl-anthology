set script-interpreter := ['uv', 'run', '--script']

@_default:
  just -l
  echo -e "\npython:"
  just -l python

# Call recipes from the Python library
mod python

# Run checks
check:
  make check

# Upgrade Hugo to new version in Github workflows & README
upgrade-hugo-version VERSION:
  sed -i 's/HUGO_VERSION: .*$/HUGO_VERSION: {{VERSION}}/' .github/workflows/*.yml
  sed -i 's/Hugo [0-9.]\+/Hugo {{VERSION}}/' README.md README_detailed.md
  sed -i 's/hugo >= [0-9.]\+/hugo >= {{VERSION}}/' README.md

# Build site and serve via Hugo's webserver
serve ENV='development' NOBIB='true':
  make NOBIB={{NOBIB}} static hugo_data bib
  cd build/ && hugo server --environment {{ENV}}

# Fetch an Anthology item and print it
[script]
print ANTHOLOGYID:
  from acl_anthology import Anthology
  from rich import print
  item = Anthology.from_within_repo().get("{{ANTHOLOGYID}}")
  print(item)

# Fetch an Anthology item and print its XML representation
[script]
print-xml ANTHOLOGYID:
  from acl_anthology import Anthology
  from acl_anthology.utils.xml import indent
  from lxml import etree
  item = Anthology.from_within_repo().get("{{ANTHOLOGYID}}").to_xml()
  indent(item)
  print(etree.tostring(item, encoding="utf-8").decode())
