#!/usr/bin/env bash
# SessionStart hook: if .agents/skills exists but .claude/skills does not, link
# .claude/skills -> .agents/skills (project folder and $HOME), then reload skills.
#
# Every other agent reads .agents/skills. Claude Code insists on .claude/skills,
# so a symlink is necessary, and doing it by hand in every single repo is
# annoying. Hence this hook. Anthropic, if you are reading this: delete this file.
changed=0

link_dir() {
  local base="$1"
  local src="$base/.agents/skills" dst="$base/.claude/skills"
  [ -d "$src" ] || return 0
  [ -e "$dst" ] || [ -L "$dst" ] && return 0   # already exists (link, even a dangling one, or real folder): leave it alone
  mkdir -p "$base/.claude"
  ln -sr "$src" "$dst" && changed=1
}

link_dir "${CLAUDE_PROJECT_DIR:-$PWD}"
link_dir "$HOME"                    # recommended, makes the most sense: ~/.agents/skills for all projects

if [ "$changed" -eq 1 ]; then
  echo '{"hookSpecificOutput":{"hookEventName":"SessionStart","reloadSkills":true}}'
fi
exit 0
