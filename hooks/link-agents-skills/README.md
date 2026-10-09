# link-agents-skills

A Claude Code `SessionStart` hook that keeps `.agents/skills` as the agent-neutral source of skills and makes Claude Code see them.

For the project folder and for `$HOME` (recommended, makes the most sense), it creates `.claude/skills` as a relative symlink to `.agents/skills`, if `.agents/skills` exists and `.claude/skills` does not. An existing `.claude/skills` (link or real folder) is never touched. When it creates a link, it asks Claude Code to reload skills.

This hook exists only because Claude Code still does not read `.agents/skills` by itself. So a symlink is necessary, and having to create it by hand in every repo is annoying. The hook does it for you.

## Install

Copy the script and register it in `~/.claude/settings.json`:

    mkdir -p ~/.claude/hooks
    cp hooks/link-agents-skills/link-agents-skills.sh ~/.claude/hooks/
    chmod +x ~/.claude/hooks/link-agents-skills.sh

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          { "type": "command", "command": "~/.claude/hooks/link-agents-skills.sh" }
        ]
      }
    ]
  }
}
```

Merge this into your existing `hooks` entry if you have one.
