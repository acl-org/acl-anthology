# Marcel Bollmann <marcel@bollmann.me>, 2019

################################################################################
# This file contains all constants and functions that have hardcoded data (such
# as URLs or journal titles) which does not come from the XML.  This is to
# provide a single file where such hardcoded data can be looked up and/or
# changed.
################################################################################

ANTHOLOGY_URL = "http://www.aclweb.org/anthology/{}"
ATTACHMENT_URL = "http://anthology.aclweb.org/attachments/{}/{}/{}"


def get_journal_title(top_level_id, volume_title):
    if top_level_id[0] == "J":
        return "Computational Linguistics"
    elif top_level_id[0] == "Q":
        return "Transactions of the Association for Computational Linguistics"
    else:
        return volume_title
