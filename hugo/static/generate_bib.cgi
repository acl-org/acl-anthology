#!/bin/bash

if [[ -z $QUERY_STRING ]]; then
    QUERY_STRING="?anthology_id=$1"
fi
anthid=${QUERY_STRING#anthology_id=}

# Set content type headers for PDF
echo "Content-Type: text/plain"
echo ""

# Get volume name
volume=$(echo $anthid | cut -d. -f1-2)

#echo "QUERY STRING $QUERY_STRING"
#echo $anthid
#echo $volume

echo "Looking for $anthid in $volume..."