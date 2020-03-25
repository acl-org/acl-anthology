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

def fake_parse(s):
    """Regexp-based parsing of possibly malformed BibTeX."""

    # Bugs:
    # - author and editor are stored as fields, not persons.

    entries = {}
    fields = {}
    bibtype = bibkey = field = None
    value = ""

    def flush_field():
        nonlocal field, value
        value = value.strip()
        if field is not None:
            # Comma after value optional
            if value.endswith(","): value = value[:-1]
            # Enclosing braces or quotes optional
            value = value.strip()
            if value.startswith("{") and value.endswith("}"): value = value[1:-1]
            elif value.startswith('"') and value.endswith('"'): value = value[1:-1]
            fields[field] = value
        elif value != "":
            logging.warning("discarded text: {}".format(value))
        field = None
        value = ""

    def flush_entry():
        nonlocal fields
        flush_field()
        if len(fields) > 0:
            entry = pybtex.database.Entry(bibtype, fields)
            if bibkey in entries:
                logging.warning("duplicate key: {}".format(bibkey))
            logging.info(str(entry))
            entries[bibkey] = entry
            fields = {}

    for line in s.splitlines():
        logging.info(line)
        # Comma after bibkey is optional
        m = re.fullmatch('\s*@([A-Za-z]+)\s*\{\s*([^\s,]*),?\s*', line)
        if m:
            flush_entry() # Closing brace optional
            bibtype = m.group(1)
            bibkey = m.group(2)
            continue

        m = re.fullmatch('\s*([A-Za-z]+)\s*=\s*(.*)', line)
        if m:
            flush_field()
            field = m.group(1)
            value = m.group(2)
            continue

        if line.strip() == '}':
            flush_entry()
        else: # Continuation of previous line
            value += '\n' + line

    flush_entry() # Closing brace optional
    return pybtex.database.BibliographyData(entries)

def read_bibtex(bibfilename):
    # Guess encoding. BibTeX is theoretically always in ASCII

    global location
    location = bibfilename
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

    if bibstring.startswith('\uFEFF'): bibstring = bibstring[1:] # Unicode BOM

    for parser in [lambda s: pybtex.database.parse_string(s, 'bibtex'),
                   fake_parse]:
        try:
            bibdata = parser(bibstring)
        except KeyboardInterrupt:
            raise
        except Exception as e:
            logging.warning("BibTeX parser raised exception '{}'; trying alternate parser".format(e))
        else:
            break
    else:
        logging.error('No more parsers; giving up.')
        return pybtex.database.BibliographyData(dict())

    return bibdata
