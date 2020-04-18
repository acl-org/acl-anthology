# Scripts for marking fixed-case words in BibTeX entries

1. Generate `truelist` by running `train.py import/*.xml`.
2. For each XML file, run `protect.py <infile> <outfile>`. This marks
   every fixed-case title word with the tag `<fixed-case>`.

Fixed-caseness is determined by these rules:

1. If a phrase (ignoring hyphens) appears in `truelist-phrases`,
   it is fixed-case. Phrases are matched greedily from left to right.
2. If a word appears in `truelist`, it is fixed-case.
3. Unless the title is in all caps (i.e. >50% of the words are all-uppercase),
   any word with a capital letter in a non-initial position (e.g.,
   "TextTiling", "QA") is fixed-case.
4. If one of a short list of adjectival modifiers including "North" and "Modern"
   precedes a fixed-case word, optionally separated by a hyphen,
   the modifier is also fixed-case. (See `amodifiers` in `protect.py`.)
5. If one of a short list of noun descriptors including "Island" and "University"
   immediately follows a fixed-case word, or precedes it separated by "of",
   the descriptor is also fixed-case. (See `ndescriptors` in `protect.py`.)
5. If a title starts with a single word set off by a colon or dash, the
   first word is fixed-case unless the word appears in an English lexicon as
   all-lowercase.
6. Otherwise, the word is not fixed-case.

Examples:

   - "Hebrew" will be fixed-case by rule 2, and "Modern Hebrew" by rule 4
   - "Carnegie" and "Mellon" will both be fixed-case by rule 2, and
     "Carnegie Mellon University" by rule 5
   - "New Mexico" will be fixed-case by rule 1, and "University of New Mexico"
     by rule 5

The `truelist` contains words from past abstracts whose most-frequent
version is not all-lowercase. To reduce the size of this list, if a
word would be marked fixed-case or not by the above rules, it is
excluded from the list.

The `truelist` in this repository has manual corrections and additions,
so please don't regenerate it.

The file `truelist-phrases` contains a manually identified selection of
multiword phrases that should be fixed-case.
