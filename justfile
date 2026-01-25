@_default:
  just -l
  echo -e "\npython:"
  just -l python

# Call recipes from the Python library
mod python

_deps:
  @make -s venv/bin/activate

# Run checks
check: _deps
  source venv/bin/activate && pre-commit run --all-files
