#!/bin/bash
# Step 3: lists all historical versions of build scripts/configs that can execute code, for READING (nothing is executed).
# (Path patterns are standard git pathspecs: "*pom.xml" also matches the root file, "**/" would not.)
# Usage: review-build-scripts.sh <repo-clone> <ecosystem>   -> output: paths per version (commit, file) + hits of suspicious patterns
set -u
REPO=${1:?repo}; ECO=${2:?ecosystem}; cd "$REPO" || exit 1
case "$ECO" in
  cargo)  PATHS=("*build.rs" ".cargo/config.toml" ".cargo/config"); PAT='Command::new|std::process|TcpStream|reqwest|curl|wget' ;;
  maven)  PATHS=("*pom.xml" ".mvn/*" "*settings.xml" "mvnw" ".mvn/wrapper/*"); PAT='exec-maven-plugin|maven-antrun|<repository>|<pluginRepository>|distributionUrl|wrapperUrl|<scripts>|groovy-maven|gmavenplus|curl|wget|bash|sh -c' ;;
  gradle) PATHS=("*build.gradle" "*build.gradle.kts" "*settings.gradle*" "gradle/wrapper/gradle-wrapper.properties" "*buildSrc/*" "*init.gradle*"); PAT='Exec|exec\(|ProcessBuilder|Runtime.getRuntime|URL\(|maven *\{|url *=|distributionUrl|apply from: *.http|curl|wget' ;;
  npm)    PATHS=("*package.json" ".npmrc" "*.yarnrc*"); PAT='"(pre|post)?install"|"prepare"|curl|wget|registry' ;;
  go)     PATHS=("go.mod" "*.go"); PAT='go:generate|exec.Command|replace ' ;;
  python) PATHS=("setup.py" "pyproject.toml" "setup.cfg"); PAT='subprocess|os.system|cmdclass|urlopen|requests' ;;
  *) echo "ecosystem?" >&2; exit 2 ;;
esac
echo "== Commits touching these files =="
git log --all --format='%h %ad %s' --date=short -- "${PATHS[@]}" | head -200
echo; echo "== Suspicious patterns in all historical versions (commit:file:line) =="
git log --all -p --format='COMMIT %h' -- "${PATHS[@]}" | grep -E "^COMMIT|^\+.*($PAT)" | awk '/^COMMIT/{c=$2;next}{print c": "$0}' | sort -u | head -300
