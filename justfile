@_default:
  just -l
  echo -e "\npython:"
  just -l python

# Call recipes from the Python library
mod python
