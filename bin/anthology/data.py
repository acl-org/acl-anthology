# -*- coding: utf-8 -*-
#
# Copyright 2019 Marcel Bollmann <marcel@bollmann.me>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

################################################################################
# This file contains all constants and functions that have hardcoded data (such
# as URLs or journal titles) which does not come from the XML.  This is to
# provide a single file where such hardcoded data can be looked up and/or
# changed.
################################################################################

ANTHOLOGY_URL = "https://www.aclweb.org/anthology/{}"
ATTACHMENT_URL = "https://www.aclweb.org/anthology/attachments/{}"


def get_journal_title(top_level_id, volume_title):
    if top_level_id[0] == "J":
        if int(top_level_id[1:3]) <= 83:
            return "American Journal of Computational Linguistics"
        else:
            return "Computational Linguistics"
    elif top_level_id[0] == "Q":
        return "Transactions of the Association for Computational Linguistics"
    else:
        return volume_title
