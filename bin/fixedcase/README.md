# Scripts for marking fixed-case words in BibTeX entries

The code and lists in this directory provide functionality to mark
every fixed-case uppercase sequence in title words with the tag `<fixed-case>`.
Any existing `<fixed-case>` tags are retained.


## Heuristics

Fixed-caseness is determined by this decision list:

1. If a full title has a case-insensitive match in `special-case-titles`, only
   the capitalized characters in the `special-case-titles` entry are fixed-case.
   This handles titles which contain stylistic all-caps in the XML.
2. If a multiword phrase (ignoring hyphens) appears in `truelist`,
   it is fixed-case. Phrases are matched greedily from left to right.
3. If a word appears in `truelist`, it is fixed-case.
4. Any word with a capital letter in a non-initial position (e.g.,
   "TextTiling", "QA") is fixed-case.
5. The French contracted forms "L’" and "D’" are not fixed-case.
6. Any tokenized word consisting of a single uppercase letter other than "A", "K" or "N",
   or a single uppercase letter plus ".", is fixed-case.
7. If one of a short list of adjectival modifiers including "North" and "Modern"
   precedes a fixed-case word, optionally separated by a hyphen,
   the modifier is also fixed-case. (See `amodifiers` in `common.py`.)
8. If one of a short list of noun descriptors including "Island" and "University"
   immediately follows a fixed-case word, or precedes it separated by "of",
   the descriptor is also fixed-case. (See `ndescriptors` in `common.py`.)
9. Otherwise, the word is not fixed-case.

Examples:

   - "Hebrew" will be fixed-case by rule 3, and "Modern Hebrew" by rule 7
   - "Carnegie" and "Mellon" will both be fixed-case by rule 3, and
     "Carnegie Mellon University" by rule 8
   - "New Mexico" will be fixed-case by rule 2, and "University of New Mexico"
     by rule 8

Note that the first word of the title is not treated specially by the rules,
so its first character will not necessarily be fixed-case.

The `truelist` contains words from past abstracts whose most-frequent
version is not all-lowercase. To reduce the size of this list, if a
word would be marked fixed-case or not by the above rules, it is
excluded from the list. The file has manual corrections and additions,
so please don't regenerate it.

The `truelist` also contains a manually identified selection of
multiword phrases that should be fixed-case.


## How to run

The main entry point is the function `protect()` in protect.py,
called on a title or booktitle node in the XML.
This updates the XML node if necessary by marking
every fixed-case uppercase sequence in title words with the tag `<fixed-case>`.
Any existing `<fixed-case>` tags are retained.

### Curating truelists

The algorithm relies on two files: `truelist` to find words/phrases
that should always include fixed-case but may not be identified by the general heuristics,
and `special-case-titles` for exceptions to the heuristics.
These lists should be augmented from time to time as new proper names arise.

1. Generate `truelist-auto` suggestions by running `train.py import/*.xml`.
2. Generate `truelist-phrasal-auto` suggestions by running `train_phrasal.py import/*.xml`.
3. Update `truelist` by curating the two lists above.
4. If there are false positives after running protect.py, add exceptions to `special-case-titles`.

### Running directly on XML files

For each XML file, run `protect.py <infile> <outfile>`.

### During ingestion process

Ingestion of a new meeting is performed by the ingest.py script in the parent directory.
It calls `normalize()` (in normalize_anth.py), which calls `protect()`
on every `"title"` and `"booktitle"` field.

When ingesting a new meeting, it is recommended to run the caser via ingest.py and then
correct any errors as follows:

* False Negatives: If a word or phrase should always have fixed-case capitals,
  add it to `truelist`. Otherwise, manually add `<fixed-case>` in the XML.

* False Positives: If the heuristics for fixed-case produce a false positive for a title,
  add it to `special-case-titles` (lowercasing all but the fixed-case capitals).
  Simply removing `<fixed-case>` from the XML runs the risk that the change
  will be overridden on a subsequent run.

Then rerun the caser (protect.py directly) on the full anthology if truelist has been modified,
or just the newly ingested meeting otherwise. Repeat if further errors are found.
