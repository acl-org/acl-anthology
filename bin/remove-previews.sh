#!/bin/bash

# Removes previews of branches that have been deleted on Github.

export PREVIEW_DIR="/var/www/preview.aclanthology.org"

set -u

if [[ -d $PREVIEW_DIR ]]; then
	cd $PREVIEW_DIR
	for branch in *; do
		# replace ___ with / for the check
		remote_branch="${branch//___//}"
		if ! curl -s -o /dev/null -f https://github.com/acl-org/acl-anthology/tree/$remote_branch; then
			echo "* Removing Anthology preview $branch"
			rm -rf "./$branch"
		fi
	done
fi
