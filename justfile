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
