#!/bin/bash
# Bisection over the first-parent list: finds the first commit from which MEASURE_CMD yields a value >= THRESHOLD.
# Usage: bisect-metric.sh <repo-clone> <commits.txt> <lo-n> <hi-n> <threshold> '<measure command, prints a number>'
# lo-n is below, hi-n above the threshold. The value must be an integer (scale decimals, e.g. per mille). The measure command runs in the checked-out state (container!).
set -u
# Safety: this script runs "git checkout -f" and "git clean -fdx" on the clone. Only inside the container (step 0).
[ -f /.dockerenv ] || [ -f /run/.containerenv ] || [ "${REPO_STORY_ALLOW_HOST:-}" = 1 ] || { echo "Refusing to run outside a container (git clean -fdx would destroy local files). Start the container first, or set REPO_STORY_ALLOW_HOST=1 on a throw-away clone." >&2; exit 3; }
REPO=$1; LIST=$2; lo=$3; hi=$4; TH=$5; CMD=$6
cd "$REPO" || exit 1
start=$(git symbolic-ref -q --short HEAD || git rev-parse HEAD)
trap 'git checkout -q -f "$start"' EXIT   # leave the clone where it was
while [ $((hi-lo)) -gt 1 ]; do
  mid=$(( (lo+hi)/2 )); sha=$(sed -n ${mid}p "$LIST")
  git checkout -q -f "$sha"; git clean -qfdx
  v=$(bash -c "$CMD" 2>/dev/null | tail -1)
  echo "n=$mid sha=${sha:0:8} value=$v" >&2
  case "$v" in ""|*[!0-9]*) echo "measure command printed no integer at n=$mid (got: '$v')" >&2; exit 2 ;; esac
  if [ "$v" -ge "$TH" ]; then hi=$mid; else lo=$mid; fi
done
echo "first commit above threshold: n=$hi $(sed -n ${hi}p "$LIST" | cut -c1-8)"
