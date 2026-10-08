# AGENTS.md

Guidelines for AI agents working in this repository.

## Language

- All skills are written in **English**: `SKILL.md`, reference files, script comments, output messages and the skill descriptions in the frontmatter.
- This applies to every file under `skills/` and to the `README.md`.
- Keep identifiers, technical terms and tool names in their original form.

## Layout

- `skills/` holds the skills developed here. This is the product that gets shared.
- `.agents/skills/` holds skills for working on this repository itself. `.claude/skills` is a symlink to it.
- `test/` is a sandbox for trying the skills: `test/.claude/skills` is a symlink to `../../skills`, so an agent started in `test/` sees them.
