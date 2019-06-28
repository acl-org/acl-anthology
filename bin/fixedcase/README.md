# Scripts for marking fixed-case words in BibTeX entries

1. Generate `truelist` by running `train.py import/*.xml`.
2. For each XML file, run `protect.py <infile> <outfile>`. This marks
   every fixed-case title word with the tag `<fixed-case>`.

Fixed-caseness is determined by these rules:

- If a word appears in an English lexicon as all-lowercase, it is not
  fixed-case.
- If a word appears in `truelist`, it is fixed-case.
- Any word with a capital letter in a non-initial position (e.g.,
  `TextTiling`) is fixed-case.
- If a title is in all caps, the above rule does not apply.
- If a title starts with a single word set off by a colon or dash, the
  first word is fixed-case.

The `truelist` contains words from past abstracts whose most-frequent
version is not all-lowercase. To reduce the size of this list, if a
word would be marked fixed-case or not by the above rules, it is
excluded from the list.

The `truelist` in this repository has manual corrections, so please
don't regenerate it.


