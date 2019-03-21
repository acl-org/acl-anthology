#!/bin/bash

# script to merge info from existing anthology xml files for CL journal
# and file J.bib from old anthology

# existing xml files include book reviews, etc, not found in J.bib
# existing xml files have authors in wrong order for years 1991-2001
#   for all papers with >2 authors
# J.bib includes page numbers

# Dan Gildea 3/21/2019

# some hand edits to J.bib
patch -o J.bib /localdisk/old_anthology/J/J.bib  J.bib.patch 

# convert bibtex to anthology xml 
# creates J??.xml in this dir
ACLPUB=. ./oldbib2anth.pl J.bib 2> log

# merged files will go into directory "new"
mkdir -p new

# merge in existing xml files
for v in J??.xml ; do
    echo $v
    python3 ./merge_sort_xml.py $v ../../data/xml/$v > new/$v 2>> log
done
