"""
Usage:
  batch_edit_name_on_papers.py AUTHORID FIRST LAST [--old OLDFIRST OLDLAST] [--except PAPERIDS ... | --only PAPERIDS ...]

Arguments:
    AUTHORID            ID of the author whose name is to be modified on papers.
    FIRST               First name to apply to retrieved papers/volumes.
    LAST                Last name to apply to retrieved papers/volumes.

Options:
    -h --help           Show this help message.
    --issue NUM         GitHub issue number to include in commit message.
    --old OLDFIRST OLDLAST    Only update the name if it matches OLDFIRST OLDLAST.
    --only PAPERIDS      Only update names on the specified paper(s)/volume(s).
    --except PAPERIDS    Skip the specified paper(s)/volume(s) when updating names.

Apply the given first and last name strings to a Person across their papers,
filtering by an existing name if OLDFIRST and OLDLAST are specified.
Includes all papers with an author that resolves to the Person, regardless of whether
the Person is verified or whether the author ID is explicit on the paper.
If necessary this will add name variants to the database (but will not remove name variants).
Optionally restrict to a subset of papers with `--only` or `--except`.
"""

import warnings
import logging as log
from docopt import docopt
from typing import Optional

from acl_anthology import Anthology
from acl_anthology.exceptions import NameSpecResolutionWarning
from acl_anthology.people import Name
from acl_anthology.utils.logging import setup_rich_logging


def batch_edit_names(
    author_id: str,
    name: Name,
    oldname: Optional[Name] = None,
    specific_paper_ids: list[str] = [],
    exclude_paper_ids: list[str] = [],
):
    assert not (specific_paper_ids and exclude_paper_ids)
    changes = f"Setting names for author {author_id} to {name.first or ''}{' | ' if name.as_full().count(' ') > 1 else ' '}{name.last}"
    anthology = Anthology.from_within_repo()

    person = anthology.get_person(author_id)
    assert person is not None, f"Could not find person: {author_id}"

    # workaround for the fact that frontmatter and volumes share namespecs

    log.info(changes)
    if oldname:
        log.info(f"Limiting to instances of current name: {oldname}")
    targets = []
    skipped = []
    namespecs = list(person.namespecs())
    for ns in namespecs:
        assert ns.parent is not None
        item = ns.parent
        item_id = item.full_id
        # note: frontmatter and Volumes share namespecs. So cannot simply check whether
        # the full_id matches the user-provided ID
        if oldname and ns.name != oldname:
            skipped.append(item_id)
            continue
        if any(
            ns is anthology.get(paper_id).get_namespec_for(person)
            for paper_id in exclude_paper_ids
        ):
            skipped.append(item_id)
            continue
        if specific_paper_ids and not any(
            ns is anthology.get(paper_id).get_namespec_for(person)
            for paper_id in specific_paper_ids
        ):
            skipped.append(item_id)
            continue
        targets.append(item_id)
        person.add_name(name)
        ns.name = name
    log.info(f"Assigned name on {len(targets)} items: {targets}")
    log.info(f"Skipped {len(skipped)} items based on flags: {skipped}")
    if specific_paper_ids:
        assert len(specific_paper_ids) == len(targets), specific_paper_ids
    elif exclude_paper_ids:
        assert len(exclude_paper_ids) <= len(skipped), exclude_paper_ids
        # some could be skipped based on oldname

    anthology.save_all()

    return changes


if __name__ == "__main__":
    args = docopt(__doc__)

    log_level = log.DEBUG if not args.get("--quiet", False) else log.INFO
    tracker = setup_rich_logging(level=log_level)
    log.getLogger("acl-anthology").setLevel(log.WARNING)
    log.getLogger("git.cmd").setLevel(log.WARNING)
    log.getLogger("urllib3.connectionpool").setLevel(log.WARNING)

    with warnings.catch_warnings(action="ignore", category=NameSpecResolutionWarning):
        name = Name(first=args["FIRST"], last=args["LAST"])
        oldname = None
        if args["--old"]:
            oldfirst, oldlast = args["--old"], args["OLDLAST"]
            oldname = Name(first=oldfirst, last=oldlast)
        msg = batch_edit_names(
            author_id=args["AUTHORID"],
            name=name,
            oldname=oldname,
            specific_paper_ids=args["--only"][0].split() if args["--only"] else [],
            exclude_paper_ids=args["--except"][0].split() if args["--except"] else [],
        )

        print(f'Now run>>> git commit -a -m "{msg}"')
