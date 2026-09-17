#!/bin/bash
# show.sh <id-prefix> [lines-after] [lines-before] — print a corpus message by its 8-char id, with context.
# Usage: ./show.sh 4b65a7c6 40 5
id="$1"; after="${2:-40}"; before="${3:-2}"
cd "$(dirname "$0")/slices" || exit 1
f=$(grep -l -- "id=${id}" slice_*.txt | head -1)
[ -z "$f" ] && { echo "id ${id} not found"; exit 1; }
n=$(grep -n -- "id=${id}" "$f" | head -1 | cut -d: -f1)
start=$(( n - before )); [ "$start" -lt 1 ] && start=1
echo "### ${f} line ${n}"
sed -n "${start},$(( n + after ))p" "$f"
