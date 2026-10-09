#!/bin/bash
# Bisection over the first-parent list: finds the first commit from which MEASURE_CMD yields a value >= THRESHOLD.
# Usage: bisect-metric.sh <repo-clone> <commits.txt> <lo-n> <hi-n> <threshold> '<measure command, prints a number>'
# lo-n is below, hi-n above the threshold. The measure command runs in the checked-out state (container!).
set -u
REPO=$1; LIST=$2; lo=$3; hi=$4; TH=$5; CMD=$6
cd "$REPO" || exit 1
while [ $((hi-lo)) -gt 1 ]; do
  mid=$(( (lo+hi)/2 )); sha=$(sed -n ${mid}p "$LIST")
  git checkout -q -f "$sha"; git clean -qfdx
  v=$(bash -c "$CMD" 2>/dev/null | tail -1)
  echo "n=$mid sha=${sha:0:8} value=$v" >&2
  if [ "${v:-0}" -ge "$TH" ]; then hi=$mid; else lo=$mid; fi
done
echo "first commit above threshold: n=$hi $(sed -n ${hi}p "$LIST" | cut -c1-8)"
