# Scripts for marking fixed-case words in BibTeX entries

1. Generate `truelist-auto` by running `train.py import/*.xml`.
2. Generate `truelist-phrasal-auto` by running `train_phrasal.py import/*.xml`.
3. Create `truelist` by curating the two lists above.
4. For each XML file, run `protect.py <infile> <outfile>`. This marks
   every fixed-case uppercase sequences in title words with the tag `<fixed-case>`.
   Any existing `<fixed-case>` tags are retained.

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
6. Any tokenized word consisting of a single uppercase letter other than "A",
   or a single uppercase letter plus ".", is fixed-case.
7. If one of a short list of adjectival modifiers including "North" and "Modern"
   precedes a fixed-case word, optionally separated by a hyphen,
   the modifier is also fixed-case. (See `amodifiers` in `common.py`.)
8. If one of a short list of noun descriptors including "Island" and "University"
   immediately follows a fixed-case word, or precedes it separated by "of",
   the descriptor is also fixed-case. (See `ndescriptors` in `common.py`.)
9. Otherwise, the word is not fixed-case.

Examples:

   - "Hebrew" will be fixed-case by rule 2, and "Modern Hebrew" by rule 4
   - "Carnegie" and "Mellon" will both be fixed-case by rule 2, and
     "Carnegie Mellon University" by rule 5
   - "New Mexico" will be fixed-case by rule 1, and "University of New Mexico"
     by rule 5

Note that the first word of the title is not treated specially by the rules,
so its first character will not necessarily be fixed-case.

The `truelist` contains words from past abstracts whose most-frequent
version is not all-lowercase. To reduce the size of this list, if a
word would be marked fixed-case or not by the above rules, it is
excluded from the list. The file has manual corrections and additions,
so please don't regenerate it.

The `truelist` also contains a manually identified selection of
multiword phrases that should be fixed-case.
