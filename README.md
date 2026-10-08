# agentic

Prompts, skills, hooks, commands, and agents for AI-assisted software modernization — designed for use with [Claude Code](https://claude.ai/code).

## What's here

| Directory | Purpose |
|-----------|---------|
| [`skills/`](skills/) | Reusable Claude Code skills (slash commands) |
| `hooks/` | Shell hooks that extend Claude Code's event lifecycle _(coming soon)_ |
| `commands/` | Custom slash commands _(coming soon)_ |
| `agents/` | Specialized sub-agent definitions for multi-agent workflows _(coming soon)_ |

## Skills

Skills are prompt files that Claude Code loads as slash commands. Drop them into `~/.claude/skills/` (or reference them from your project's `.claude/` directory) to activate them.

| Skill | Description |
|-------|-------------|
| [code-fitness-map](skills/code-fitness-map/) | Rates every source file of a codebase (Java, JavaScript, TypeScript, Python, C#, Go and more) fit (blue), strained (violet) or unfit (red) by code fitness, oriented at ideas of Adam Tornhill. Measures smells (Complex/Large Method, Nested Complexity, Excess Arguments, Duplication, Brain Method/Class, Developer Congestion) with lizard and Git, weighted in a readable `weights.yaml`. Outputs a CSV, a summary, and a zoomable bubble chart that shows "unhealthy and changing" code. Deterministic, no LLM. |
| [dependency-map](skills/dependency-map/) | Finds the dependencies between artifacts that language tools such as jdeps or madge do not see: names shared between code, XML, JSON, JSP, properties and SQL, classes looked up by string or bean id, URLs between templates and servlets, shared database tables, and files that change together in Git. Writes a typed edge list with evidence and confidence per edge, plus an explanatory notebook. |
| [git-repo-trust-audit](skills/git-repo-trust-audit/) | Audits a repository's git history to judge how far it can be trusted as ground truth: author identity consistency, commit message quality, history rewrites, squash-merge granularity, and message/diff correspondence. Gives a verdict per dimension plus an overall recommendation before you lean on `git log`/`blame` for "who" and "why" questions. |
| [java-symbolic-renaming](skills/java-symbolic-renaming/) | Rename or improve a Java identifier using symbolic tools (LSP, Serena, OpenRewrite, ast-grep). Handles risk classification, alternative name proposals, and safe execution. |
| [jupyter-notebook](skills/jupyter-notebook/) | Does traceable, step-by-step work in Jupyter notebooks using literate programming: data analyses and transformations, migration scripts, ETL, codebase exploration, and other multi-step tasks where every step from input to result should be understandable. Distinguishes neutral, reusable *method notebooks* from system-specific *evidence notebooks*, which get a timestamped interpreted copy with an assessment of the results in marked cells. Validates every notebook with `nbformat`. |
| [mikado-graph](skills/mikado-graph/) | Plan and track complex refactorings using the Mikado Method. Produces a dependency graph (DOT/SVG) that shows what to do first and surfaces non-obvious coupling. |

## Philosophy

Modern software rarely needs to be rewritten — it needs to be understood and incrementally improved. The tools here are built around that idea:

- **Symbolic over textual** — prefer rename tools that understand code structure over find-and-replace
- **Incremental over big-bang** — surface blockers early, make safe leaf-node changes first
- **Transparent artifacts** — generate reviewable plans (DOT graphs, YAML recipes, shell scripts) before executing anything
