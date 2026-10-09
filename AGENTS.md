# AGENTS.md

Guidelines for AI agents working in this repository.

## Language

- All skills are written in **English**: `SKILL.md`, reference files, script comments, output messages and the skill descriptions in the frontmatter.
- This applies to every file under `skills/` and to the `README.md`.
- Keep identifiers, technical terms and tool names in their original form.

## Agent-agnostic skills

- Skills must work with any coding agent, not only Claude Code. This is the default and is not advertised in the skills.
- Do not describe a skill as "a Claude Code skill" and do not claim agent independence in `SKILL.md` or the skill's `README.md`. Just write neutral instructions.
- Do not rely on tools or features of one specific agent. Use plain markdown, shell, Python and containers.
- Mentioning Claude Code is fine for install paths (e.g. `~/.claude/skills/`) or when the skill is about it.

## Layout

- `skills/` holds the skills developed here. This is the product that gets shared.
- `test/` is a sandbox for trying the skills: `test/.claude/skills` is a symlink to `../../skills`, so an agent started in `test/` sees them.
