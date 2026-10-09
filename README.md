# agentic

Prompts, skills, hooks, commands, and agents for Agentic Software Modernization.

## Philosophy

*If you can tool it, tool it. If you can't, prompt it.* (via Torben Keller)

Modern software rarely needs to be rewritten — it needs to be understood and then incrementally improved. The tools here are built around that idea, in that order.

**Understand first**

- **Facts from the system, not from the model's memory** — tools produce the facts: deterministic metrics, claims re-measured instead of believed, plans built from real code, history and runs instead of the training corpus. The model interprets and displays in an understandable way, but is never the source of truth
- **Show provenance and limits** — every finding names its evidence and confidence, says what it does not cover, and marks interpretation as interpretation
- **Leave the original alone** — inputs are read-only, foreign code runs in a container, and results are reproducible from the top for everyone

**Then change safely**

- **Symbolic over textual** — prefer tools that understand code structure over find-and-replace
- **Incremental over big-bang** — surface blockers early, make safe leaf-node changes first
- **Review before execute** — generate the plan or artifact first, and let a person confirm it before anything runs

## What's here

| Directory | Purpose |
|-----------|---------|
| [`skills/`](skills/) | Reusable agent skills |
| [`hooks/`](hooks/) | Shell hooks that extend Claude Code's event lifecycle |
| `commands/` | Custom slash commands _(coming soon)_ |
| `agents/` | Specialized sub-agent definitions for multi-agent workflows _(coming soon)_ |

## Skills

Skills are prompt files with scripts and reference material. They are not active in this repo: an agent started in the repo root does not load them.

- **Try them:** start your agent in `test/`. `test/.agents/skills` and `test/.claude/skills` link to `../../skills`, so only that folder sees them.
- **Install one:** link or copy its folder into your agent's skills directory, e.g. `ln -s "$PWD/skills/repo-story" ~/.claude/skills/repo-story`. A link keeps it in sync with the repo.

**How the skills are built**

- **Tool first, prompt second** — whatever a script can do deterministically (measure, replay, render, validate) is a script. The prompt covers only what a tool cannot: choosing, interpreting, writing.
- **Facts come from tools, interpretation from the model** — the output keeps the two apart, so a reader can see what was measured and what was concluded.
- **Every skill states its limits** — what it does not cover and which numbers are own decisions or proxies, so nobody mistakes a lead for a finding.
- **Plain and portable** — markdown, shell, Python and containers. Nothing ties a skill to one agent.
- **Small core, details on demand** — `SKILL.md` holds the workflow and the rules, `references/` the details, `scripts/` and `assets/` the tools.

| Skill | Description |
|-------|-------------|
| [code-fitness-map](skills/code-fitness-map/) | Rates every source file of a codebase (Java, JavaScript, TypeScript, Python, C#, Go and more) fit (blue), strained (violet) or unfit (red) by code fitness, oriented at ideas of Adam Tornhill. Measures smells (Complex/Large Method, Nested Complexity, Excess Arguments, Duplication, Brain Method/Class, Developer Congestion) with lizard and Git, weighted in a readable `weights.yaml`. Outputs a CSV, a summary, and a zoomable bubble chart that shows "unhealthy and changing" code. Deterministic, no LLM. |
| [dependency-map](skills/dependency-map/) | Finds the dependencies between artifacts that language tools such as jdeps or madge do not see: names shared between code, XML, JSON, JSP, properties and SQL, classes looked up by string or bean id, URLs between templates and servlets, shared database tables, and files that change together in Git. Writes a typed edge list with evidence and confidence per edge, plus an explanatory notebook. |
| [git-repo-trust-audit](skills/git-repo-trust-audit/) | Audits a repository's git history to judge how far it can be trusted as ground truth: author identity consistency, commit message quality, history rewrites, squash-merge granularity, and message/diff correspondence. Gives a verdict per dimension plus an overall recommendation before you lean on `git log`/`blame` for "who" and "why" questions. |
| [java-symbolic-renaming](skills/java-symbolic-renaming/) | Rename or improve a Java identifier using symbolic tools (LSP, Serena, OpenRewrite, ast-grep). Handles risk classification, alternative name proposals, and safe execution. |
| [jupyter-notebook](skills/jupyter-notebook/) | Does traceable, step-by-step work in Jupyter notebooks using literate programming: data analyses and transformations, migration scripts, ETL, codebase exploration, and other multi-step tasks where every step from input to result should be understandable. Distinguishes neutral, reusable *method notebooks* from system-specific *evidence notebooks*, which get a timestamped interpreted copy with an assessment of the results in marked cells. Validates every notebook with `nbformat`. |
| [mikado-graph](skills/mikado-graph/) | Plan and track complex refactorings using the Mikado Method. Produces a dependency graph (DOT/SVG) that shows what to do first and surfaces non-obvious coupling. |
| [repo-story](skills/repo-story/) | Repo archaeology: rebuilds a project's git history commit by commit in an isolated container, re-measures what commit messages claim, finds jumps by bisection, and turns the result into a designed PDF article plus carousel slides (12 or 6 pages, English and German) with an optional post text. Measure first, then write. Themeable design (neutral default, your own colors in one command). Rust, Java, Node, Go and Python prepared. |

## Hooks

| Hook | Description |
|------|-------------|
| [link-agents-skills](hooks/link-agents-skills/) | `SessionStart` hook for Claude Code. Keeps `.agents/skills` as the agent-neutral source of skills: if `.claude/skills` is missing, it creates it as a symlink to `.agents/skills`, for the project folder and for `$HOME` (recommended), and reloads skills. Saves creating the symlink by hand in every repo. |