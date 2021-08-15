#!/usr/bin/env bash

# Copyright 2021 Marcel Bollmann <marcel@bollmann.me>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Script structure partly based on
# https://gist.github.com/m-radzikowski/53e0b39e9a59a1518990e76c2bff8038

### NOTE --- may still be buggy and not always do the correct thing, proceed
### with caution...

set -o errexit      # Exit on most errors (see the manual)
set -o nounset      # Disallow expansion of unset variables
set -o pipefail     # Use last non-zero exit code in a pipeline
trap cleanup SIGINT SIGTERM ERR EXIT

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd -P)
cd "${SCRIPT_DIR}/.."

usage() {
  cat <<EOF
Usage: $(basename "${BASH_SOURCE[0]}") [-h] [-n] branch-or-commit [branch-or-commit]

Builds the Anthology website twice from two different branches/commits, diffs
them and reports changes.

Arguments:
  Branches or commits (i.e. anything that can be passed to `git checkout`) to
  compare.  If only one is given, the second will be set to the currently
  checked-out commit.

Available options:
  -h, --help      Print this help and exit
  -e, --exist-ok  Re-use existing build directories
  -n, --nobib     Do not build bib files
EOF
  exit
}

msg() {
    echo >&2 -e "${1-}"
}

die() {
    local msg=$1
    local code=${2-1} # default exit status 1
    msg "$msg"
    exit "$code"
}

cleanup() {
  trap - SIGINT SIGTERM ERR EXIT
  set +o errexit
  set +o nounset
  cd "${SCRIPT_DIR}/.."
  if [[ -n "${rev1_dir}" && -d ${rev1_dir} ]]; then
      msg "${RED}* Leaving build directory ${YELLOW}${rev1_dir}${RED}; delete manually if desired${NOFORMAT}"
  fi
  if [[ -n "${rev2_dir}" && -d ${rev2_dir} ]]; then
      msg "${RED}* Leaving build directory ${YELLOW}${rev2_dir}${RED}; delete manually if desired${NOFORMAT}"
  fi
  if [[ -n "${tmpfile}" && -f ${tmpfile} ]]; then
      rm -f "${tmpfile}"
  fi
  if [[ -n "$current_head" ]]; then
      if [[ $(git rev-parse --short HEAD) != $current_head ]]; then
          git checkout $current_head
      fi
  fi
  die "exited early"
}

setup_colors() {
    if [[ -t 2 ]] && [[ -z "${NO_COLOR-}" ]] && [[ "${TERM-}" != "dumb" ]]; then
        NOFORMAT='\033[0m' RED='\033[0;31m' GREEN='\033[0;32m' ORANGE='\033[0;33m' BLUE='\033[0;34m' PURPLE='\033[0;35m' CYAN='\033[0;36m' YELLOW='\033[1;33m'
    else
        NOFORMAT='' RED='' GREEN='' ORANGE='' BLUE='' PURPLE='' CYAN='' YELLOW=''
    fi
}

parse_params() {
    # default values of variables set from params
    nobib=false
    existok=0

    while :; do
        case "${1-}" in
            -h | --help) usage ;;
            -n | --nobib) nobib=true ;;
            -e | --exist-ok) existok=1 ;;
            -?*) die "Unknown option: $1" ;;
            *) break ;;
        esac
        shift
    done

    args=("$@")

    # check required params and arguments
    [[ ${#args[@]} -eq 0 ]] && usage
    [[ ${#args[@]} -gt 2 ]] && die "Expected at most 2 arguments; got ${#args[@]}"

    rev1=$(git rev-parse --short ${args[0]} 2>/dev/null) || die "Not a valid branch-or-commit: ${args[0]}"
    if [[ ${#args[@]} -eq 2 ]]; then
        rev2=$(git rev-parse --short ${args[1]} 2>/dev/null) || die "Not a valid branch-or-commit: ${args[1]}"
    else
        rev2=$(git rev-parse --short HEAD)
    fi

    rev1_dir=build-${rev1}
    rev2_dir=build-${rev2}
    if [[ -d "$rev1_dir" && $existok -eq 0 ]]; then
        die "Build directory ${rev1_dir}/ already exists; please delete it or provide -e/--exist-ok to re-use it"
    fi
    if [[ -d "$rev2_dir" && $existok -eq 0 ]]; then
        die "Build directory ${rev2_dir}/ already exists; please delete it or provide -e/--exist-ok to re-use it"
    fi

    return 0
}

setup_colors
parse_params "$@"

which md5sum >/dev/null 2>&1 || die "This script needs `md5sum` but it's not on your $PATH; please install it"
diff_name=diff-${rev1}-${rev2}
current_head=$(git rev-parse --short HEAD)

msg "${GREEN}* Comparing ${YELLOW}${rev1}${GREEN} to ${YELLOW}${rev2}${GREEN} with nobib=${YELLOW}${nobib}${NOFORMAT}"

if [[ -d "$rev1_dir" ]]; then
    msg "${ORANGE}* Re-using existing build directory ${YELLOW}${rev1_dir}${ORANGE}; skipping build${NOFORMAT}"
else
    make clean
    msg "${GREEN}* Building site with revision ${YELLOW}${rev1}${GREEN}...${NOFORMAT}"
    git checkout $rev1
    NOBIB=$nobib make -j4 site
    mv build $rev1_dir
fi

if [[ -d "$rev2_dir" ]]; then
    msg "${ORANGE}* Re-using existing build directory ${YELLOW}${rev2_dir}${ORANGE}; skipping build${NOFORMAT}"
else
    make clean
    msg "${GREEN}* Building site with revision ${YELLOW}${rev2}${GREEN}...${NOFORMAT}"
    git checkout $rev2
    NOBIB=$nobib make -j4 site
    mv build $rev2_dir
fi

msg "${GREEN}* Preparing build directories for diff'ing...${NOFORMAT}"

# HTML files encode commit name and build time, which is not informative for diff'ing
find $rev1_dir -name "*.html" -exec sed -i 's/<i>Site last built.*<\/a>\.<\/i>//' {} \;
find $rev2_dir -name "*.html" -exec sed -i 's/<i>Site last built.*<\/a>\.<\/i>//' {} \;

msg "${GREEN}* Computing MD5 checksums...${NOFORMAT}"

cd $rev1_dir
cs1="${SCRIPT_DIR}/../diff.${rev1}.md5"
find . -type f -exec md5sum {} + | sort -k 2 > "${cs1}"
cd "${SCRIPT_DIR}/.."
cd $rev2_dir
cs2="${SCRIPT_DIR}/../diff.${rev2}.md5"
find . -type f -exec md5sum {} + | sort -k 2 > "${cs2}"
cd "${SCRIPT_DIR}/.."

summary="${SCRIPT_DIR}/../diff.${rev1}-${rev2}.summary.txt"
tmpfile=$(mktemp)

set +o errexit
trap - ERR EXIT

echo "Files only in ${rev1}:" >> $summary
diff --changed-group-format="" --unchanged-group-format="" --old-group-format="%<" --new-group-format="" \
     "${cs1}" "${cs2}" | sed 's/^[0-9a-f]\+ \+//' > $tmpfile
cat $tmpfile >> $summary
echo "" >> $summary
echo -e -n "${BLUE}"
printf "%6d" $(cat "$tmpfile" | wc -l)
echo -e "${NOFORMAT} files only exist in ${YELLOW}${rev1}${NOFORMAT}"

echo "Files only in ${rev2}:" >> $summary
diff --changed-group-format="" --unchanged-group-format="" --old-group-format="" --new-group-format="%>" \
     "${cs1}" "${cs2}" | sed 's/^[0-9a-f]\+ \+//' > $tmpfile
cat $tmpfile >> $summary
echo "" >> $summary
echo -e -n "${BLUE}"
printf "%6d" $(cat "$tmpfile" | wc -l)
echo -e "${NOFORMAT} files only exist in ${YELLOW}${rev2}${NOFORMAT}"

echo "Files that differ:" >> $summary
diff --changed-group-format="%<" --unchanged-group-format="" --old-group-format="" --new-group-format="" \
     "${cs1}" "${cs2}" | sed 's/^[0-9a-f]\+ \+//' > $tmpfile
cat $tmpfile >> $summary
echo "" >> $summary
echo -e -n "${BLUE}"
printf "%6d" $(cat "$tmpfile" | wc -l)
echo -e "${NOFORMAT} files differ between ${YELLOW}${rev1}${NOFORMAT} and ${YELLOW}${rev2}${NOFORMAT}"
echo "       ...of which there are:"
echo -e -n "${BLUE}"
printf "%6d" $(grep ".html\$" "$tmpfile" | wc -l)
echo -e "${NOFORMAT} .html files"
echo -e -n "${BLUE}"
printf "%6d" $(grep ".yaml\$" "$tmpfile" | wc -l)
echo -e "${NOFORMAT} .yaml files"
if [[ $nobib == "false" ]]; then
    echo -e -n "${BLUE}"
    printf "%6d" $(grep ".bib\$" "$tmpfile" | wc -l)
    echo -e "${NOFORMAT} .bib files"
fi

rm -f "$tmpfile"

msg "${GREEN}* Report written to ${YELLOW}${summary}${NOFORMAT}"

if [[ $(git rev-parse --short HEAD) != $current_head ]]; then
    git checkout $current_head
fi
