---
name: code-fitness-map
description: Rate every source file of a codebase (Java, JavaScript, TypeScript, Python, C#, C/C++, Go, Rust, Kotlin, Scala, Swift, PHP, Ruby) fit (blue), strained (violet) or unfit (red) by code fitness, oriented at ideas of Adam Tornhill (smells per file, three categories). Smells are Brain Class, Brain Method, Complex Method, Large Method, Nested Complexity, Excess Arguments, Code Duplication and Developer Congestion, measured with lizard, an own nesting scanner and Git, and weighed in a readable weights.yaml. Writes a CSV per file, a summary per unit and a hierarchical bubble chart (zoomable circle packing), with change days next to the fitness so "unfit and changing" becomes visible. Deterministic, seconds to a minute, no LLM. Use for "code fitness", "which code is hard to change", "fitness map", "technical debt hotspots", "bubble chart by code fitness".
---

# Code Fitness Map

One question: **how fit is this code to change?** Not how much autonomy an agent gets there (that is `blast-radius-map`; using this result as a signal there is not wired up yet) and not which concepts exist.

The colours: **blue (fit)** easy to change, **violet (strained)** complex with maintenance issues and higher defect risk, **red (unfit)** severe technical debt. They say nothing about blast radius: unfit code that nobody depends on is red here.

## The idea behind it

Oriented at ideas of Adam Tornhill, kept explicit and our own:

- Fitness is a property of a **file**, made of **code smells** that predict how hard the code is to change: Brain Class, Brain Method, Complex Method, Large Method, Deep Nesting, Excess Arguments, Duplication and people-side smells like Developer Congestion.
- Three categories, **fit, strained, unfit** (blue, violet, red), aggregated by **lines of code**, and read together with how often the code changes.
- The levels come from a readable weighted sum of smell counts in `weights.yaml`. All thresholds and weights are our own decisions, marked `[own]`. Brain Method, Brain Class and Code Duplication are proxies; Bumpy Road, Complex Conditional, Low Cohesion and Primitive Obsession are not measured at all.

Provenance of every number in `weights.yaml`: `[own]` our decision, `[proxy]` our stand-in for a smell without an agreed numeric definition.

## Principles

- **Every number has a provenance** (`[own]`, `[proxy]`). Do not change a threshold in the script, change it in `weights.yaml` and say why.
- **Orient at the idea, never claim equivalence.** The map is our own construction; do not present a level as a validated measure of a file.
- **Never present a proxy as the real smell.** Brain Class and Brain Method are proxies; Bumpy Road, Complex Conditional, Low Cohesion and Primitive Obsession are **not measured**. Every report says so.
- **Fitness and change are separate.** The colour is fitness only. Change days in the window are their own column and their own colour mode ("unfit and changing"), because "unfit" and "unfit and touched often" ask different questions.
- **A human reads the weights before the map counts.** The first run proposes; look at the distribution and decide whether the weights fit this codebase.

## Procedure

1. **Check the prerequisites.** Sources in a supported language (see `EXT` in the script), Git history, and two Python packages: `lizard` and `PyYAML`. Nothing is installed for you. Without a `.mailmap`, authors are counted per name and the congestion signal is weaker; say so.
2. **Look at the weights.** Show `weights.yaml` to the human in short: which smells, which thresholds, which are `[own]` and which `[proxy]`, and ask whether they fit this codebase. Check `scope.exclude` too: vendored third-party code in the repository (bundled libraries) is analysed unless excluded.
3. **Run the script** (writes only into `--out`):

   ```
   uv run --no-project --with lizard --with pyyaml python -I <skill dir>/scripts/fitness.py [--repo <path>] [--out <folder>] [--config <weights.yaml>] [--active-authors <file>]
   ```

   Default output folder `temp/code-fitness-map`. Look into an existing target folder before writing to it. With `lizard` and `PyYAML` installed, `python3 -I <skill dir>/scripts/fitness.py` works as well. Runtime is seconds to about a minute for a codebase of a thousand files.
4. **Read the distribution, not just the map.** How many files unfit, strained, fit, and which smell makes the unfit files unfit. If one detector decides almost all unfit files, it is too coarse: tune the weights or the proxy, and write down why.
5. **Report what is missing.** `fitness.md` ends with the smells that were not measured, and says whether the former-contributors signal was possible.
6. **Hand over.** Offer the CSV for CodeCharta and the bubble chart. The fitness level could become a signal in `blast-radius-map`, in its own column; that is not wired up yet.

## What the script measures

| Smell | Measured by | Quality |
|---|---|---|
| Complex Method | lizard cyclomatic complexity per function, `[own]` 9 (alert 100) | heuristic |
| Large Method | lizard code lines per function, `[own]` 70 (alert 500); anonymous functions are skipped | heuristic |
| Nested Complexity | own scanner: deepest nesting of conditionals and loops, an `else` block counts as a level, `[own]` 4 | heuristic |
| Excess Arguments | lizard parameter count, `[own]` more than 4 | heuristic |
| Large file, Overall Code Complexity | code lines `[own]` 1000 (alert 5000), mean complexity `[own]` 4 | heuristic |
| Code Duplication | functions of at least 10 code lines whose token structure is at least 85 % similar to a sibling in the same file | proxy |
| Brain Method | complex AND large AND deeply nested AND more than 4 arguments | proxy |
| Brain Class | a Brain Method in a file of at least 500 lines and 20 functions (`[own]`) | proxy |
| Developer Congestion | distinct authors in the window, `[own]` 5 | verified |
| Complex code by former contributors | only with a list of active people, otherwise missing | verified / missing |

The window for change days, authors and congestion ends at the **last change to the sources**, not at today: a codebase whose history ended in 2023 would otherwise show no change at all. Mass commits (more than `ignore_commits_over_files` files) are left out.

## Tools that go well with it

Hints, not requirements. Use what the environment already has and pick the way you would pick anyway.

- **Running the script:** `uv run --with ...` (as above) needs no install and leaves nothing behind; `pipx run` or a throwaway `venv` with `pip install lizard pyyaml` do the same job.
- **Reading the result:** `fitness.csv` opens in any spreadsheet, DuckDB, `pandas` or `csvkit`; `bubbles.html` needs only a browser. For example `duckdb -c "select path, level, change_days from 'fitness.csv' order by change_days desc limit 20"`.
- **Other views on the same CSV:** CodeCharta (path comes first for it) for a 3D city map; hotspot tools such as `code-maat` or `git-of-theseus` to put the history next to the fitness.
- **Cleaner author counts:** a `.mailmap` in the repository, and `git shortlog -sne` to see which identities need merging.
- **Cross-checking single files:** the same functions in `lizard` directly (`lizard <file>`), and `cloc` or `tokei` for the line counts.

## Output

```
fitness.csv       one row per file: level, score, a count per smell, change days, authors, worst function (path first, for CodeCharta)
fitness.md        overall share by lines of code, units worst first, unfit and changing files, what was not measured
bubbles.html     hierarchical bubbles: a folder is a circle around its files, click to zoom in; area = lines of code;
                 colour = fitness, change days, or unfit-and-changing; works offline
bubbles.artifact.html   the same page for publishing (d3 from a CDN)
```

Aggregation is by **lines of code**, not by file count: a 5000-line file weighs more than ten small ones.

## Limits

- Languages are the ones in `EXT` in the script (lizard knows more; add the extensions there). The nesting scanner counts braces, so for Python and Ruby the nesting depth is not measured and Nested Complexity is skipped (the report says so). The detectors were developed on Java and JavaScript; check another language against a few files you know before trusting it.
- Brain Method, Brain Class and Code Duplication are proxies; the weights are our decisions and have not been validated; look at the distribution on your own codebase.
- The nesting scanner is not a parser. It is tolerant of comments, strings and braceless bodies but can be wrong on regex literals and unusual constructs.
- Test code is out of scope for this version.
