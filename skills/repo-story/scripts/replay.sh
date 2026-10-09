#!/bin/bash
# Replays the history: ONE build/check command per first-parent commit. Runs INSIDE the container. Resumable.
# Usage:  ECOSYSTEM=maven replay.sh <repo-clone> <results-folder> [REF=main]
# ECOSYSTEM: cargo | maven | gradle | npm | go | python | custom   (table and background: references/ecosystems.md)
# Overridable via environment: BUILD_CMD, BUILD_FILES (space-separated, at least one must exist), DEP_FAIL_RE, TIMEOUT (seconds)
# Second pass (e.g. with tests): use a different BUILD_CMD and a different <results-folder>.
# Status: ok | fail | dep_fail (dependencies not resolvable / lock does not match, do NOT silently re-resolve) | no_build_file | checkout_failed
set -u
REPO=${1:?repo-clone}; OUT=${2:?results-folder}; REF=${3:-main}
ECO=${ECOSYSTEM:-custom}
case "$ECO" in
  cargo)  F="Cargo.toml";                  C="cargo check --workspace --locked";                         D='lock file|--locked' ;;
  maven)  F="pom.xml";                     C='$( [ -x ./mvnw ] && echo ./mvnw || echo mvn ) -B -q -DskipTests test-compile'; D='Could not resolve|Non-resolvable|Could not transfer|Could not find artifact' ;;
  gradle) F="build.gradle build.gradle.kts settings.gradle settings.gradle.kts"; C='$( [ -x ./gradlew ] && echo ./gradlew || echo gradle ) --no-daemon -q testClasses'; D='Could not resolve|Could not GET|Could not HEAD|Plugin .* was not found' ;;
  npm)    F="package.json";                C="npm ci --ignore-scripts && npm run build --if-present";    D='npm ci|package-lock|ERESOLVE|E404' ;;
  go)     F="go.mod";                      C="go build ./...";                                           D='go.sum|updates to go.mod needed|cannot find module' ;;
  python) F="pyproject.toml setup.py requirements.txt"; C="python -m compileall -q .";                   D='' ;;
  custom) F="${BUILD_FILES:-}";            C="${BUILD_CMD:-}";                                           D="${DEP_FAIL_RE:-}" ;;
  *) echo "unknown ECOSYSTEM: $ECO" >&2; exit 2 ;;
esac
BUILD_FILES=${BUILD_FILES:-$F}; BUILD_CMD=${BUILD_CMD:-$C}; DEP_FAIL_RE=${DEP_FAIL_RE:-$D}; TIMEOUT=${TIMEOUT:-1800}
[ -n "$BUILD_CMD" ] || { echo "no BUILD_CMD (ECOSYSTEM=custom needs BUILD_CMD)" >&2; exit 2; }
mkdir -p "$OUT/logs"; cd "$REPO" || exit 1
git rev-list --first-parent --reverse "$REF" > "$OUT/commits.txt"
[ -f "$OUT/results.csv" ] || echo "n,sha,date,status,seconds,subject" > "$OUT/results.csv"
has_build_file() { [ -z "$BUILD_FILES" ] && return 0; for f in $BUILD_FILES; do [ -f "$f" ] && return 0; done; return 1; }
n=0
while read -r sha; do
  n=$((n+1))
  grep -q "^$n,${sha:0:8}," "$OUT/results.csv" && continue
  git checkout -q -f "$sha" || { echo "$n,${sha:0:8},,checkout_failed,0," >> "$OUT/results.csv"; continue; }
  git clean -qfdx
  date=$(git log -1 --format=%ad --date=short); subj=$(git log -1 --format=%s | tr ',"' ';\047' | cut -c1-90)
  log="$OUT/logs/$(printf %03d $n)-${sha:0:8}.log"; t0=$(date +%s)
  if ! has_build_file; then status=no_build_file
  elif timeout "$TIMEOUT" bash -c "$BUILD_CMD" >"$log" 2>&1; then status=ok
  elif [ -n "$DEP_FAIL_RE" ] && grep -qE "$DEP_FAIL_RE" "$log"; then status=dep_fail
  else status=fail; fi
  echo "$n,${sha:0:8},$date,$status,$(( $(date +%s)-t0 )),$subj" >> "$OUT/results.csv"
done < "$OUT/commits.txt"
echo done > "$OUT/replay.done"
