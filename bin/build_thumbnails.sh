#!/bin/bash

# Builds thumbnails for files. There are two use cases:
# 1. If no arguments are supplied, will do so for all Anthology files.
#
#    Example:
#
#        build_thumbnails.sh
#
# 2. If two arguments are supplied, will read the first file and write
#    to the second.
#
#    Example:
#
#        build_thumbnails ~/anthology-files/pdf/W/W19/W19-5605.pdf \
#          ~/anthology-files/thumb/W/W19/W19-5606-thumb.pdf
#
# The first use case recurses to the second.

# The base directory of Anthology object files (contains pdf/ and thumb/)
ANTHOLOGYFILES=$HOME/anthology-files

# Where to write thumbnails
THUMBDIR=${ANTHOLOGYFILES}/thumb

# Thumbnail dimensions
DIM=600

if [[ -z $2 ]]; then
    [[ ! -e $THUMBDIR ]] && mkdir -p $THUMBDIR

    for pdf in $(find $ANTHOLOGYFILES/pdf/ -type f -name '*.pdf'); do
        outfile=$THUMBDIR/$(basename $pdf .pdf).jpg
        if [[ ! -s $outfile ]]; then
          echo "$pdf -> $outfile"
          bash $0 $pdf $outfile
        fi
    done
else
    pdffile=$1
    outfile=$2

    convert $pdffile[0] -background "#FFFFFF" -flatten -resize x${DIM}^ -gravity North -crop ${DIM}x${DIM}+0+10 -colorspace Gray $outfile
fi
