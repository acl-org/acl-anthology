@_default:
  just -l
  echo -e "\npython:"
  just -l python

# Call recipes from the Python library
mod python

# Run checks
check:
  make check

# Build site and serve via Hugo's webserver
serve ENV='development' NOBIB='true':
  make NOBIB={{NOBIB}} static hugo_data bib
  cd build/ && hugo server --environment {{ENV}}
