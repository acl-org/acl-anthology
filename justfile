@_default:
  just -l


# Access commands from the Python library (`just -l python` to list them)
mod python


# Run type-checker on a single file, intended for bin/ files
[no-cd]
typecheck FILE:
     env MYPYPATH={{justfile_directory()}}/python mypy --follow-imports silent {{FILE}}
