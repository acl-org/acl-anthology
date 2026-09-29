This directory contains data files shaped like the [actual data
files](https://github.com/acl-org/acl-anthology/blob/master/data/) of the
Anthology, in order to serve as a basis for writing test cases for the Python
library.  **All content in this directory — every collection, paper, person,
venue, and SIG — is entirely fabricated.** Any resemblance to real people,
papers, venues, or events is coincidental and unintentional; none of it should
ever be treated as factually correct, and it must **never** be overwritten
with real Anthology data.

Only the *structure* of these files (element/field shapes, ID formats, edge
cases such as missing page numbers, many-author papers, or diacritic names)
is meaningful and deliberately preserved to exercise specific library
behavior — the substance is invented. If you add new fixture content, keep
inventing: don't copy real proceedings text or real people's names/ORCIDs in
here, even in part.

These files are covered by the [Apache-2.0
License](https://github.com/acl-org/acl-anthology/blob/master/LICENSE).
