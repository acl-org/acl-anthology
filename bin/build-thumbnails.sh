# Requires $PREVIEW_DIR to be set.
#!/bin/bash

# Builds thumbnails and trimmed thumbnails for all PDFs.
# (Trimmed thumbnails are used in the Metadata edit screen.)
# The script works by echoing commands to STDOUT, which should
# be piped through xargs or GNU parallel.
#
# There are two use cases:
# 1. If no arguments are supplied, it will recurse to the base case:
#
#    Example:
#
#        build_thumbnails.sh | parallel -j 5
#
# 2. In the base case, the thumbnail and trimmed thumbnail files are provided.
#    These are echoed to STDOUT.

# The base directory of Anthology object files (contains pdf/ and thumb/)
ANTHOLOGYFILES=$HOME/anthology-files

# Where to write thumbnails
THUMBDIR=${ANTHOLOGYFILES}/thumb

# Thumbnail dimensions
DIM=600

if [[ -z $2 ]]; then
    [[ ! -e $THUMBDIR ]] && mkdir -p $THUMBDIR

    inputdir=${1:-$ANTHOLOGYFILES/pdf/}
    for pdf in $(find $inputdir -type f -name '*.pdf'); do
        outfile=$THUMBDIR/$(basename $pdf .pdf).jpg
        trimmedfile=$THUMBDIR/$(basename $pdf .pdf)-trimmed.jpg
        # update if outfile doesn't exist or has an older timestamp
        if [[ ! -e $outfile || ! -e $trimmedfile || $pdf -nt $outfile ]]; then
          echo bash $0 $pdf $outfile $trimmedfile
        fi
    done
else
    pdffile=$1
    outfile=$2
    trimmedfile=$3

    convert $pdffile[0] -background white -flatten -resize x${DIM}^ -gravity North -crop ${DIM}x${DIM}+0+10 -colorspace Gray $outfile

    DIM=1024
    convert $pdffile[0] -background white -colorspace Gray -flatten -resize x${DIM}^ -gravity North -crop ${DIM}x${DIM}+0+10 -trim $trimmedfile
fi
