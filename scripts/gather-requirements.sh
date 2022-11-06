#!/bin/bash

set -euo pipefail

__dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

annotate() {
    while read line
    do
        echo -e "$line\t# $@"
    done
}

# requirements.txt
for file in $*
do
    ext="${file##*\.}"
    if [ "$ext" == "txt" ]
    then
        grep -v '\W*#' "$file" | annotate "$file"
    elif [ "$ext" == "py" ]
    then
        "${__dir}"/setup-py-to-requirements.py "$file" | annotate "$file"
    elif [ "$ext" == "cfg" ]
    then
        "${__dir}"/setup-cfg-to-requirements.py "$file" | annotate "$file"
    fi
done | sort | column -t
