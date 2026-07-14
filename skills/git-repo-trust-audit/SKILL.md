---
name: git-repo-trust-audit
description: Audit a repository's git history to judge how trustworthy it is as ground truth — commit message quality, author identity consistency, history rewrites, squash-merge granularity, and message/diff correspondence. Use when the user asks whether git history can be relied on, before leaning on git log/blame for "why" or "who" questions, or when onboarding to an unfamiliar or legacy repository.
---

# Git Trustworthiness Audit

Assess whether this repository's git history is reliable enough to use as ground truth for
"who changed what," "when," and "why" questions. Produce a verdict per dimension plus an
overall recommendation. Git is always mechanically authoritative about *current file state*;
this audit is about whether the *narrative* (messages, authorship, granularity) can be trusted.

Run the checks below with Bash. If the user names a subdirectory or time range, scope the
commands accordingly (`-- <path>`, `--since=<date>`).

The example commands use fixed sample sizes (`-n 500`, 5 spot checks, etc.) — treat these
as starting points, not fixed parameters. Scale to the repository: audit the full history
when it's small enough to be cheap, sample more when early results look suspicious or
inconsistent, and pick sample sizes that make the percentages meaningful. Always state in
the report what was actually examined. The same goes for grep patterns and thresholds
throughout: they encode common conventions and rules of thumb, and you should adapt them
to what you actually see in this repository.

## Check 1 — Author identity consistency

The same person often commits under multiple name/email pairs (work vs. private email, GitHub
noreply address, laptop misconfiguration, name typos). This silently corrupts any "who did
what" analysis.

```bash
git shortlog -sne --all
```

Then look for likely duplicates. Common patterns (examples, not an exhaustive list — judge
each pair by asking "could these plausibly be the same person?"):
- Same email, different names
- Same or near-identical name, different emails (especially `*@users.noreply.github.com`
  paired with a real address)
- Nickname/handle vs. real-name pairs (e.g. a GitHub handle in one, full name in another)
- Case or diacritic variants of the same name
- Work vs. private email for the same name, or an old employer's domain next to a new one

Separate out automation accounts (dependabot, renovate, CI bots, `actions@github.com`) —
they are not duplicates of anyone and should be counted as bots, not contributors.

Also check whether a `.mailmap` file exists at the repo root. If it exists, rerun
`git shortlog -sne --all` (mailmap is applied automatically) and note which duplicates it
already resolves.

**Report:** number of distinct identities, suspected duplicate clusters, whether `.mailmap`
exists. If duplicates are found and no `.mailmap` exists, propose the exact `.mailmap`
content that would consolidate them — but only *propose* it; do not create the file unless
the user asks. Ask the user to confirm ambiguous clusters (two similar names may genuinely be
two people).

## Check 2 — Commit message quality

```bash
git log --format='%s' -n 500
```

Read the subjects and classify them by judgment — the terms below are illustrative
examples of each category, NOT a keyword list to grep for. A subject like `more stuff`,
`fixes again`, or a low-effort message in another language is just as low-signal even
though it matches no example. Length filters and word lists only surface candidates;
you decide the classification by reading them.

- **Low-signal:** conveys nothing about the change — e.g. single words like `fix`, `wip`,
  `update`, keyboard noise like `asdf` or `.`, or vague phrases like `changes`, `stuff`
- **Mechanical-only:** describes the diff but not the intent — e.g. `rename variable`,
  `add file`
- **Informative:** says what and ideally why

Also measure how many commits have a body at all:

```bash
git log --format='%b|' -n 500 | grep -c '^|$'
```

**Report:** percentage of low-signal subjects and percentage with no body. Rough bands:
under 10% low-signal = good; 10–40% = mixed; over 40% = poor (treat messages as unreliable
for intent).

## Check 3 — History granularity (squash/merge patterns)

Squash-merged history makes `git blame` point at big merge commits instead of the real
author and moment of a line change.

```bash
git log --format='%s' -n 500 | grep -ciE '\(#[0-9]+\)$|^Merge pull request'
git log --format='%h' --min-parents=2 -n 500 | wc -l
```

Also check typical commit size — huge average diffs suggest squashing or bulk imports:

```bash
git log --shortstat --format='%h' -n 200 | grep -E 'files? changed' | \
  awk '{f+=$1; n++} END {if (n) printf "avg files/commit: %.1f over %d commits\n", f/n, n}'
```

**Report:** share of squash/merge commits and average commit size. High squash share means
"who wrote this line" answers are coarse (PR-level, not line-level) — blame identifies the
merger, not necessarily the author.

## Check 4 — History rewrites and force pushes

Rewritten history erases or falsifies the original trail. Local evidence is limited, but check:

```bash
git reflog --date=iso | grep -iE 'reset|rebase|amend' | head -20
git log --format='%ci %ai %h %s' -n 200 | awk '{if ($1 != $4) print}' | head -20
```

The second command finds commits whose author date differs from commit date — normal for
rebases and cherry-picks, but a *large share* of them means history was heavily rewritten.
Also compare local vs. remote if a remote exists (`git rev-list --left-right --count
HEAD...@{upstream}` where configured).

**Report:** signs of rewriting and what that means: timestamps and ordering may not reflect
when work actually happened.

## Check 5 — Message/diff correspondence (spot check)

Pick 5 commits spread across history (recent, middle, old — use `git log --format='%h' | sed -n
'1p;25p;100p;250p;500p'` or similar) and for each compare the message to the actual diff:

```bash
git show --stat <hash>
```

Does the message describe what the diff actually does? A message saying "fix typo" over a
300-line refactor is a red flag that messages are disconnected from content.

**Report:** how many of the sampled commits had messages matching their diffs.

## Check 6 — Coverage gaps

```bash
git log --format='%ci' -n 1                       # newest commit
git log --format='%ci' --reverse | head -1        # oldest commit
git log --format='%ci' -n 500 | cut -d- -f1,2 | sort | uniq -c   # commits per month
```

Look for: a truncated start (repo imported without history — first commit is a giant
"initial import"), long dark gaps, or a shallow clone (`git rev-parse --is-shallow-repository`).
Check the first commit's size: `git show --stat $(git rev-list --max-parents=0 HEAD | head -1)`.

**Report:** whether history covers the project's real lifetime or starts at an import
boundary. An "Initial commit" containing thousands of files means everything before that
date is invisible to git.

## Collecting evidence

While running the checks, save the raw command output that supports each rating — you will
need it for the report. For each dimension keep a small evidence sample, not full dumps:

- Identity: the full `git shortlog -sne --all` output (usually short) with suspected
  duplicate clusters grouped
- Messages: 10 example low-signal subjects with their hashes, and 3 informative ones for
  contrast
- Granularity: 5 example squash/merge subjects with their diffstat line
- Rewrites: the divergent author/commit date lines found (up to 10)
- Correspondence: for each of the 5 sampled commits, the message plus its `--stat` summary
  and whether they match
- Coverage: first/last commit dates, the commits-per-month histogram, and the initial
  commit's diffstat

## Final report

Summarize as a table with one row per dimension (identity, messages, granularity, rewrites,
correspondence, coverage), each rated **good / mixed / poor** with the one number or fact
that justifies the rating. Then give an overall verdict in plain prose:

- What git **can** be trusted for in this repo (usually: current state, coarse who/when)
- What it **cannot** be trusted for here (e.g. intent, line-level authorship, pre-import history)
- Concrete remediation, in order of impact — typically: add a `.mailmap` (include the proposed
  content), adopt a commit message convention going forward, avoid squash merges if line-level
  blame matters

## HTML report

After presenting the verdict in the conversation, also produce an HTML report unless the
user asked for terminal output only. If the `artifact-design` skill is available, load it
before writing the page and follow its design guidance. Write a single self-contained HTML
file (inline CSS, no external resources) to the scratchpad directory, or to a path the
user names.

Structure:

1. **Header** — repo name, audit date, commit range examined (e.g. "500 most recent of
   1,240 commits"), overall verdict badge
2. **Summary table** — the six dimensions with their good/mixed/poor rating (color-coded:
   green/amber/red) and the justifying number
3. **One section per dimension** — the rating, a one-paragraph explanation, and the evidence
   sample collected above rendered as `<pre>` blocks or small tables. Show real data: actual
   commit hashes, subjects, author lines, diffstats. Hashes make findings verifiable —
   the reader can run `git show <hash>` themselves.
4. **Recommendations** — the remediation list; if a `.mailmap` is proposed, include its full
   content in a copy-friendly code block
5. **Method note** — which commands were run and any sampling limits, so the report is
   reproducible

Keep it printable: no JavaScript required, sensible in both light and dark (use
`prefers-color-scheme`). Wide `<pre>` content must scroll horizontally inside its own
container. If the Artifact tool is available and the user wants a shareable page, publish
the same file via Artifact; otherwise just report the file path.

Do not modify the repository during the audit. All checks are read-only; the only artifact
you may offer to create is a `.mailmap`, and only with the user's confirmation. The HTML
report goes to the scratchpad, not the repo, unless the user explicitly asks to keep it
in the repository.
