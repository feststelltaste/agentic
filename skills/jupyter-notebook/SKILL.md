---
name: jupyter-notebook
description: Performs traceable work step by step in Jupyter notebooks using literate programming – data analyses, data transformations, migration scripts, ETL, codebase exploration with generated follow-up artifacts, exploratory investigations, and any other multi-step procedural task where every step from input to result should be understandable. Always use whenever the task involves creating or working in a Jupyter notebook. Trigger phrases - "Jupyter", "notebook", "ipynb", "traceable analysis", "migration script in a notebook", "analyze raw data", "step by step with documentation".
---

# Jupyter Notebook: traceable work, step by step

Goal: a notebook that reads top to bottom and makes every step from the starting point (raw data,
source system, input files) to the result (visualization, migrated data, report, final state)
traceable. Literate programming: text explains, code does.

Typical uses: data analysis, data cleaning and transformation, migration scripts, ETL, API or
database exploration, codebase exploration (finding things by heuristics and generating work
from the hits), one-off investigations, reproducible reports.

## Two kinds of notebook: method and evidence

Decide first which of the two you are writing; the rules below apply to both, but the emphasis differs.

| | **Method notebook** (neutral, reusable) | **Evidence notebook** (specific to one system) |
|---|---|---|
| Purpose | A method that can be dropped into other projects and run there | Proof of one analysis of one system, read by people |
| Specific to | Nothing: all system details are settings in the configuration cell | One system, one commit: names real files, shows real findings |
| Code examples | Not needed; small inline tests on synthetic cases show the method works | **Required**: code cells that read the real lines and display them (file, line, hit marked), so the reader sees what depends on what |
| Interpretation | None in the notebook; it stays neutral | **Required**: an interpreted copy (see "After the run") that weighs the results |
| Markdown | Method and why, never data | Method and why, never data (examples and findings come from code cells and the interpreted copy) |
| Helpers | As few as possible, so it stays easy to copy | A small helper for display (e.g. showing a source snippet) is fine |

An evidence notebook is usually fed by the scripts of a neutral method. Do not copy system-specific names, numbers or paths into the method notebook; do not strip the examples and interpretation out of an evidence notebook.

### Readable with the code folded

An evidence notebook is read by people who never unfold a code cell, so it must make sense with the code hidden:

- **Fold the code.** Set `metadata["jupyter"] = {"source_hidden": True}` and the tag `hide-input` on every code cell except the configuration cell, which stays open so the reader can see and change the settings.
- **Every output says what it is.** No bare `(14899, 7)` or unlabeled table: print one sentence first (`print(f"{len(edges):,} edges read from {EDGES_CSV}; the first five:")`), give figures a title, and let tables follow a markdown cell that names them.
- **A passing check says so.** An assertion that passes shows nothing, so print one line after it (`check passed: ...`); with the code folded this is the only sign that the check ran. Failing stays loud (`assert`).
- **No library noise** in the outputs (warnings, progress bars); fix the cause or suppress it at the source.
- Check the result once with `jupyter nbconvert --to markdown --no-input --stdout <file>.ipynb` and read it as the reader would.

## Core principles

1. **Inputs stay untouched.** Raw data and source systems are only read, never overwritten. Every
   change happens in the notebook as a visible processing step and writes to a separate output.
2. **Every step is visible.** No hidden preprocessing in helper scripts or pre-generated files.
   Whatever the result depends on is in the notebook.
3. **One idea per code cell.** Small, focused cells. One cell loads, one filters, one transforms,
   one writes, one plots.
4. **Check intermediate results.** Look at them and assert them (see the assertions section). After important steps, take a quick look (`df.head()`,
   `df.shape`, `df.info()`, `value_counts()`, row counts before/after, quick matplotlib plots) to
   confirm the step did the right thing. This includes intermediate analyses.
5. **Reproducible top to bottom.** "Restart & Run All" must always work. No dependence on cell
   execution order or on state left over from deleted cells.

## Additional rules for tasks with side effects (migrations, writes, imports)

- **Separate preparing from applying.** Build and inspect the planned changes first (dry run,
  preview of what would be written), then apply them in a clearly marked, separate cell.
- **Make destructive or outward-facing steps explicit.** Gate them behind a named flag in the
  configuration cell (e.g. `APPLY = False`) and mention them in the preceding markdown cell.
  Confirm with the user before running anything irreversible against a real system.
- **Prefer idempotent steps** that can safely be re-run, or state clearly when a cell must only be
  run once.
- **Verify after applying.** Add check cells that compare the result against the source (row
  counts, key sets, checksums, spot checks) so the migration proves itself.
- **Keep a trail.** Log what was changed, skipped or failed in a DataFrame or list that is visible
  in the notebook rather than only printing to a console.

## Example: investigating a codebase or file tree

Not only tabular data: a notebook can also trace work on a codebase, a file tree, a repository
history or a set of documents. Typical questions: where is X used? Which parts are hotspots?
What would a change touch? What does the inventory look like?

The shape is usually the same, whatever the question:

1. **Collect raw facts** with simple, visible means – file listings and globs, grep/regex over
   contents, `git log` output, parsed config files, build or dependency descriptors, metrics
   from existing tools. Each source or heuristic is its own cell and its own named result
   (`files`, `commits`, `matches_by_regex`, `matches_by_import`).
2. **Put the facts into DataFrames** (one row per file, commit, match, …, plus which heuristic or
   source found it) so they are inspectable, filterable and countable.
3. **Check the heuristics.** Compare independent ones where possible (overlap, only-in-one),
   spot-check false positives and misses before trusting a result.
4. **Combine and refine** in visible steps: join sources (e.g. change frequency from the
   history × size or complexity per file), deduplicate, exclude, classify, rank, aggregate.
5. **Present or derive the result:** a ranked table, a plot, a report, or – if the work should
   continue – generated artifacts (rules, scripts, configuration, tickets, a work list) written
   to a separate output directory, never into the source tree directly.
6. **Verify:** the output matches the list it was derived from; where a tool exists, a dry run
   against the sources.

Examples of questions with this shape (language- and domain-neutral):

- Code hotspots: commit history per file combined with size or complexity, ranked.
- Usage of a custom string-based DSL (e.g. a homegrown query language embedded in string
  literals): find the call sites and string patterns, classify by variant, count per module.
- Candidates for a rename, deprecation or migration: find by naming or structure rules, check,
  then generate the instructions for the tool that applies it.
- Dependency or technology inventory across many repositories or modules.

## Assertions and small tests: fail loudly

The notebook must **fail** when something does not add up, instead of silently producing a wrong
result. Use plain `assert` with a message (ideally showing the offending rows) at the important
points:

- **After loading:** expected columns present, row count above zero, key columns unique and
  without missing values, dtypes as expected.
- **After each transformation:** row counts before/after as expected (no accidental fan-out
  from a join, no lost rows), no unexpected NaN, values within valid ranges or sets.
- **Before writing or applying:** the planned changes are non-empty, free of collisions and
  duplicates, and only touch what they should.
- **After writing or applying:** the result matches the source (counts, key sets, checksums).

```
assert not duplicates.any(), duplicates.head()
assert len(merged) == len(left), f"join changed row count: {len(left)} -> {len(merged)}"
```

**Small inline tests** at important points: a cell with a few concrete, hand-checked cases for
a non-trivial step (a regex, a mapping rule, a parsing or derivation step, a join key). Use a
small DataFrame or Series of inputs with the expected outputs and compare them with an assert
(`pd.testing.assert_series_equal`, `assert_frame_equal`, `assert_index_equal`). Prefer these over a
plain `==` check: on failure they show exactly where and how the values differ. Loosen them only
as far as needed (`check_dtype=False`, `check_names=False`, `check_like=True` to ignore row and
column order, `rtol`/`atol` for floats). Clearly mark such cells
as test steps in the preceding markdown cell (what is being tested and why, no data findings).
Include edge cases the real data is known or likely to contain (empty values, odd spellings,
names that are substrings of others).

**Keep it proportionate.** Assert and test where a wrong result would be costly or easy to miss
(joins, regexes, mappings, writes), not after every line. A few meaningful checks beat a wall of
them; no tests for trivial steps, and no more test cases than needed to cover the risky edges.

Assertions must not depend on the current data values in a way that makes the notebook brittle
for no reason; assert invariants and rules, not incidental numbers.

## Markdown cells: the what and why, never the data

Every code block is preceded by a markdown cell that describes **what happens in the following
code and why** – in prose, concise, in the language the user is working in.

- Describe intent and method ("We filter to completed study visits because only those are to be
  migrated."), not results.
- **No concrete data, numbers or findings** in markdown cells (not "There are 1,234 rows, the mean
  is 5.6"). The data lives in the cell outputs; the text stays valid even if the data changes.
- Structure with headings, adapted to the task. For an analysis: question → load → inspect/clean →
  transform → analyze → visualize → summary of the approach. For a migration: goal → read source →
  map/transform → preview → apply → verify.
- The first markdown cell states the goal and the sources (paths, systems – not contents).
- The only exception is the **interpretation cells of the interpreted copy** (see "After the run: the interpreted copy"): they assess one run and therefore name its numbers. They never go into the original notebook.

## Code style: procedural, elegant, standard tools

- Standard tools: **pandas**, **numpy** if needed, **matplotlib** (also for intermediate checks);
  standard library or the usual drivers/clients (`sqlite3`, `requests`, `sqlalchemy`, …) for I/O.
  No exotic dependencies without a reason.
- **Procedural and linear, no classes, and no `def` functions where avoidable.** The code works
  directly in the cell, top to bottom. A helper function is a last resort, only if the same logic
  is truly needed several times and cannot be expressed as a pandas operation.
- **Pandas does the work, directly on plain text in the cell.** Read files/text into a DataFrame
  or Series and use pandas functions instead of loops: `.str.extract()`, `.str.findall()`,
  `.str.replace()` (also with a callable), `.str.contains()`, `.map()`, `.explode()`, `.merge()`
  (also cross joins), `.groupby().agg()`, string concatenation of columns to build text output.
  No `for` loops over rows/files/matches when a vectorized pandas expression exists; a list
  comprehension only to collect inputs (e.g. file paths) into the first DataFrame.
- Idiomatic pandas: method chaining (`.assign()`, `.query()`, `.pipe()`, `.groupby().agg()`),
  vectorized operations instead of loops, named aggregations, `.loc` instead of chained indexing.
  Watch for NaN in string filters (`na=False`).
- Descriptive variable names for every intermediate state (`raw`, `cleaned`, `per_visit`,
  `planned_changes`) instead of `df`, `df2`, `df3`. One intermediate state = one name.
- Code comments sparingly, only for the why of a non-obvious line. The explanation belongs in the
  markdown cell.
- Randomness (if used) with a fixed seed.

## Configuration: all settings in the first code cell

**Every setting the user might want to change lives in the very first code cell** (right after
the title/goal markdown cell), so the user can steer the whole notebook from one place without
scrolling or reading code. No setting may be hidden further down in the notebook.

What belongs in there (as named UPPER_CASE constants, grouped with short comment headers):

- **Paths and directories:** input roots, output directories, file names.
- **File selection:** file extensions, glob patterns, include/exclude patterns, ignored
  directories (`.git`, `node_modules`, `target`, `__pycache__`, `vendor`, …), size limits.
- **Exceptions and exclusions:** skip lists, allow lists, known false positives, special cases.
- **URLs and endpoints:** base URLs, API paths, database connection strings (without secrets).
- **Thresholds and parameters:** limits, batch sizes, date ranges, regexes, magic numbers, random
  seed, row limits for previews.
- **Flags:** `APPLY = False`, `DRY_RUN`, verbosity, whether to overwrite existing outputs.
- **Secrets:** never hardcoded; read from the environment (`os.environ["…"]`) and name the
  variable in the configuration.

Rules:

- The configuration block comes **first**, before imports are used for anything else (imports may
  sit directly above it or be part of the same cell, but the settings are visible at the top).
- Later cells only **reference** these constants; no literals for paths, extensions, URLs,
  exclusions or thresholds inline in the code. If a new setting becomes necessary while building
  the notebook, add it to the first cell, not next to the code that uses it.
- Prefer plain Python literals (strings, lists, sets, dicts) with a one-line comment per setting
  explaining what it controls and what values are valid.
- The configuration cell contains **only settings, no imports**. Imports come in their own cell
  after the dependency installation (see next section).
- Derived values (e.g. `OUTPUT_DIR.mkdir(...)`, compiled regexes) go into the cell that first
  needs them, not into the configuration block, so the block stays a pure list of settings.

## Dependencies: install in a bash cell, before the imports

All third-party packages are installed **up front in a dedicated code cell** that calls bash, so
the notebook runs on a fresh environment without manual preparation:

```
%%bash
pip install --quiet pandas matplotlib pyyaml
```

The order at the top of the notebook is: title/goal (markdown) → configuration (code, settings
only) → dependencies (markdown + `%%bash` cell) → imports (markdown + code). Every package the
notebook imports must be listed in the install cell. Non-Python tools the notebook needs (e.g.
`mvn`, `php`, `jq`) are checked there too (`command -v php`).

## Visualization

- Matplotlib with explicit axis labels, title and units; `fig, ax = plt.subplots(...)`.
- One message per plot; choose a suitable chart type (distribution → histogram/box, trend → line,
  comparison → bar).
- **Use matplotlib for intermediate visualization wherever it helps understanding or checking**,
  not only for the final result. Good moments: after loading (distributions, missing values),
  after a join or filter (before/after counts), when comparing heuristics or sources (overlap,
  only-in-one), for outliers and unexpected values, and before applying changes (what would be
  affected, grouped). Skip a plot when a `head()` or a `value_counts()` already shows it clearly.
- Intermediate plots are explicitly welcome and clearly marked as check steps in the preceding
  markdown cell (what is being checked and why, no findings). Keep them quick: plain defaults,
  but still with axis labels and a title.
- For the design of final visualizations, load the `dataviz` skill if available.

## Workflow

1. **Check the environment:** are Jupyter/ipykernel and the needed libraries available? If not,
   install them, or ask briefly if the environment is unclear. Create and edit the notebook with
   `nbformat` or the NotebookEdit tool.
2. **Look at the inputs first**, before assumptions make their way into code: structure, dtypes,
   missing values, value ranges, schemas – and document this in the notebook.
3. **Build incrementally:** markdown cell → code cell → inspect output → next step. Do not write
   the whole notebook in one go without executing in between.
4. **Execute and validate:** run the whole notebook top to bottom with
   `jupyter nbconvert --to notebook --execute --inplace <file>.ipynb` (or papermill); fix errors
   until it runs cleanly. Keep the outputs in the notebook so the result is readable without
   re-execution. (For notebooks with side effects, execute with the apply flag off unless the
   user approved applying.)
5. **Validate the file:** after every creation or edit, check that the `.ipynb` is a valid
   notebook and contains no error outputs. Use `nbformat` (no extra script needed):
   ```
   python3 -c "
   import nbformat, sys
   nb = nbformat.read(sys.argv[1], as_version=4)
   nbformat.validate(nb)
   errors = [o for c in nb.cells if c.cell_type == 'code' for o in c.outputs if o.output_type == 'error']
   assert not errors, f'{len(errors)} error outputs'
   print('valid,', len(nb.cells), 'cells')
   " notebook.ipynb
   ```
   Do this again after the final execution. A notebook that fails validation is not delivered.
   **Read the warnings.** The check above only finds errors. After every execution also search the outputs for warnings (`stderr` streams, `Warning` in text outputs, deprecation and
   `SettingWithCopy` messages) and read each one. Fix the cause (a regex with capture groups, chained indexing, a deprecated argument, a dtype mix); suppress a warning only when it
   is understood and harmless, and then at the narrowest place with a comment saying why, never globally. Run again until no warning is left, and say in the wrap-up if one remains
   on purpose.
6. **Clean up:** remove unused cells and imports, keep cells in logical order, leave no error
   output or debug leftovers.
7. **Interpreted copy (evidence notebooks only):** once the notebook has run cleanly and is validated, make the timestamped
   copy with an assessment of the important results (next section). Method notebooks skip this step; for an evidence notebook skip it only if the user
   said so.
8. **Wrap up:** tell the user where the notebook (and, for an evidence notebook, the interpreted copy) is, what the notebook does
   (the approach, without inflating it with data values), the main points of the assessment, and what
   remains open or uncertain (e.g. assumptions made during cleaning or mapping).

## After the run: the interpreted copy

**Only for evidence notebooks** (see "Two kinds of notebook"). A method notebook gets no interpreted copy; it stays free of findings so it can be reused elsewhere.

When the evidence notebook has run top to bottom without errors and passed validation, make a **copy that adds an assessment of the results**. The original stays as it is: its markdown is free of
data, it is the one source and it can be re-run. The copy documents one run.

1. **Copy** the executed notebook next to the original as `<topic>-<YYYYMMDD-HHMMSS>-<version>.ipynb`. `<version>` is the version state of the repository: the short commit hash
   (`git rev-parse --short HEAD`), with `-dirty` appended if there are uncommitted changes (`git status --porcelain` is not empty), or `nogit` outside a Git repository. Take the
   timestamp from the clock when the copy is made. Never overwrite an earlier copy, and do not run the copy again: it keeps the outputs of the run it documents. Directly under the
   title add one marked cell that says when the copy was made, from which repository state and from which notebook.
2. **Read the copy from top to bottom.** Read every output, and look at each figure with the image viewer instead of guessing from the code. After each **important** result add one
   **interpretation cell**. Important means: what answers the question of the notebook, a surprising value, a result that rests on a heuristic or a sample, a check that passed
   narrowly. Not every `head()` and not every intermediate table.
3. **End with an overall assessment cell** at the bottom: the answer to the question of the notebook, how far to trust it, and what to do or check next.
4. **Mark every interpretation cell the same way**, so that it can be told from the author's markdown at a glance: a light-blue box, and the tag `interpretation` in the cell
   metadata so that the cells can be found or removed again. Use exactly this form (the blank lines inside the box are needed for the Markdown in it to render):

   ```
   <div style="background:#e8f1fb; border-left:4px solid #2a78d6; padding:8px 14px; color:#1d1f23;">

   **Interpretation**

   ...the text...

   </div>
   ```

   With `nbformat`: `cell = nbf.v4.new_markdown_cell(text); cell.metadata["tags"] = ["interpretation"]`, inserted after the code cell whose result it assesses. The text colour is
   set so that the box stays readable in a dark theme.
5. **Validate the copy** with `nbformat` as in the workflow. The code cells and their outputs must be the same as in the original; only the marked cells are new.

What an interpretation says, and does not say:

- **What the result shows**, with the concrete numbers from the output (here numbers belong: the cell assesses this one run), then **what it means for the question**, **how far to trust
  it** (sample or full data, heuristic or measured, checks done or not, missing data) and **what would change the conclusion**.
- Keep **observation, inference and open question apart**, as separate short parts or clearly labelled sentences.
- Write only what the outputs support. Mark a guess as a guess. Do not name a cause that the notebook did not examine.
- Short: a few sentences that can be read in a minute. In the language the user works in.
- The author's cells are not changed, moved or removed.

## Where notebooks live

All notebooks go into the `notebooks/` directory in the repository root, one subdirectory per
notebook (named after its topic, kebab-case):

```
notebooks/<topic>/<topic>.ipynb
notebooks/<topic>/<topic>-<YYYYMMDD-HHMMSS>-<version>.ipynb   # interpreted copies, one per documented run
notebooks/<topic>/output/        # everything the notebook generates (OUTPUT_DIR = "output")
```

Paths in the configuration cell for outputs are relative to the notebook, so the notebook and
its results stay together. Generated output that can be reproduced by re-running the notebook
may be added to `.gitignore`; suggest it to the user, don't decide silently. The interpreted copies are results of a run, not sources: whether to keep them in version control is the user's decision too. Run
`jupyter nbconvert` from the notebook's directory.

## Notebook skeleton (orientation, adapt to the task)

1. Markdown: title, goal, sources
2. Code: **configuration first** – all settings (paths, file extensions, exclusions, URLs,
   thresholds, flags), settings only, no imports
   2b. Markdown + code (`%%bash`): install dependencies
   2c. Markdown + code: imports
3. Markdown + code: load inputs (`raw`), first look (`head`, `info`, `shape`)
4. Markdown + code: quality checks (missing values, duplicates, value ranges)
5. Markdown + code: cleaning/transformation/mapping in named steps
6. Markdown + code: analysis/aggregation or preview of planned changes, with intermediate checks
7. Markdown + code: visualization(s) or applying the changes (gated)
8. Markdown + code: verification of the result
9. Markdown: summary of the approach and assumptions

## Don't

- Don't let a failing check pass silently: no `try/except` around asserts, no `print("warning")` instead of an assert.
- Don't hardcode result numbers or data contents in markdown cells.
- Don't scatter settings (paths, extensions, exclusions, URLs, thresholds) across cells; they all
  belong in the first code cell.
- Don't overwrite raw data or silently write intermediate states to disk or to external systems.
- No huge catch-all cells; no loops and no `def` helper functions where pandas can do it directly.
- Don't import packages that the bash install cell doesn't install.
- Don't deliver a notebook that hasn't run completely at least once.
- Don't leave warnings in the outputs unread: read them, fix the cause, or suppress them narrowly with a reason. No global `warnings.filterwarnings("ignore")`.
- Don't write interpretation into the original notebook, don't re-run the interpreted copy, and don't interpret every cell: only the important results, each in a marked light-blue cell.
- Don't interpret from the code alone: read the outputs and look at the figures first.
