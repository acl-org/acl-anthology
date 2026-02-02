# utils.ids

!!! warning

    **Importing these functions outside of the library is usually unnecessary.**

    - Collection items already provide IDs in both string form (`full_id`) and tuple form (`full_id_tuple`), as well as a `year` attribute.
    - Person objects have `is_explicit` corresponding to checking if their ID is verified.
    - ID validation functions are called automatically upon modifying relevant attributes, so you probably just want to set them directly and check for an exception.

::: acl_anthology.utils.ids
