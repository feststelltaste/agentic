# Method in detail (ecosystem-neutral)

Concrete commands per language: `ecosystems.md`. A worked example (Rust, 516 commits): `example-photocraft.md`.

## Environment (step 0)
- Container as an unprivileged user (`--cap-drop=ALL`, `no-new-privileges`, `--pids-limit`). Template: `assets/devcontainer/`. Working folder as the only bind mount, dependency cache as a **named volume owned by the container user**.
- Clone of the original inside the working folder, push disabled (`git config remote.origin.pushurl DISABLED`). Never mount the original repo, never commit.
- No credentials inside: no host `$HOME`, no settings files with tokens, no environment variables with secrets.
- **Pitfall:** if the cache volume belongs to `root`, the first run fails with permission errors and is worthless. Point the cache directory to a writable volume via an environment variable. Move the first run to `results-invalid-<reason>/`, document the reason, measure again.
- If the build needs network (almost always): allow access only to the package sources where possible. Report anything suspicious (unexpected connections, writes outside the working and cache folders, odd build scripts) immediately and stop.
- Missing hardware (GPU, display) is environment, not a commit failure. Software rendering is often enough for UI images.

## Step 1: Replay
`scripts/replay.sh` (see header comment). First-parent list, `git clean -qfdx` per commit, time limit, CSV `n,sha,date,status,seconds,subject`, one log per commit, resumable. Status: `ok`, `fail`, `dep_fail`, `no_build_file`, `checkout_failed`. **Never silently re-resolve dependencies** (pulls current, unvetted versions); where there is no lock file, that is a limit of the method and belongs in the report.

## Step 2: Plausibility
- "ok in 0 to 1 s": check whether code was really changed there (`git show --stat`) or the build tool did nothing (incremental cache!). **Cold sample** with an empty build folder (10 commits).
- Second pass with tests/examples/benches: finds what "compiles" does not see.
- Format/lint across all commits, if possible without running project code.
- Read numbers from commit messages and checked-in report files per commit and re-measure at key points.
- Evaluation: stretches of red commits, longest stretch, what fixed it, whether the message names the cause and whether that is true.

## Step 3: Read third-party code
`scripts/review-build-scripts.sh <repo> <ecosystem>`: all historical versions of build scripts and configurations that can execute code, plus hits of suspicious patterns. Read, confirm, put the result in the report. Third-party dependencies run along but are not reviewed individually: state that as a limit.

## Step 4: Deepen key commits
15 to 20 states with tests, fuzz/property tests, lints, reference data. Verify SHAs via `git log --grep`. A test that only appears late is measured only from there on. Decide beforehand which metrics to collect per state (test count, module count, lines, coverage, one project-specific number).

## Step 5: Oracle and bisection
- **Oracle:** reference output of the original or of a comparison system. Same tolerance at all measuring points.
- **Bisection:** `scripts/bisect-metric.sh`. Measure only the part that jumps. Result: first commit from which it flips; hold its message against the measurement.
- Produce a difference image/diff where errors may be invisible to the eye.

## Playing through cases
Three patterns have proven useful: a **community batch** (many merges within minutes, then a repair commit), a **jump found by bisection**, a **finding from fuzzing/property tests**. For each: sequence according to the history, intermediate results measured per commit, images or excerpts, "What the case shows".

## Additional sources
AGENTS.md / CLAUDE.md / CONTRIBUTING (rules, completion checklist, parallel work), README (self-image, outdated numbers), roadmap/scorecard (honest gaps), architecture docs, CI configuration (what it really enforces, since when). From these: design decisions, order, guardrails.
