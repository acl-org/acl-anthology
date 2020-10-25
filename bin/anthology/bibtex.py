# -*- coding: utf-8 -*-
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

import copy
import re
import logging
import pybtex, pybtex.database.input.bibtex


def read_bibtex(bibfilename):
    """
    Reads bibtex data from a file into pybtex data structures.
    """

    bibbytes = open(bibfilename, "rb").read()
    bibstring = None
    for encoding in ['ascii', 'utf8', 'cp1252']:
        try:
            bibstring = bibbytes.decode(encoding)
        except UnicodeDecodeError:
            continue
        logging.debug("{}: using {} encoding".format(bibfilename, encoding))
        break
    else:
        logging.warning("couldn't figure out encoding; using ascii with escapes")
        bibstring = bibbytes.decode('ascii', 'backslashreplace')

    if bibstring.startswith('\uFEFF'):
        bibstring = bibstring[1:]  # Unicode BOM

    # for parser in [lambda s: pybtex.database.parse_string(s, 'bibtex'),
    #                fake_parse]:
    try:
        bibdata = pybtex.database.parse_string(bibstring, "bibtex")
    except:
        import sys

        print(f"Failed to parse {bibfilename}", file=sys.stderr)
        sys.exit(1)
    return bibdata
