#!/bin/bash

# Removes previews of branches that have been deleted on Github.
# Requires $PREVIEW_DIR to be set.

. ~/.bashrc

set -eu

if [[ -d $PREVIEW_DIR ]]; then
	cd $PREVIEW_DIR
	for branch in *; do
		curl -s -o /dev/null -f https://github.com/acl-org/acl-anthology/tree/$branch
		if [[ $? -ne 0 ]]; then
			echo "* Removing Anthology preview $branch"
			rm -rf "./$branch"
		fi
	done
fi
