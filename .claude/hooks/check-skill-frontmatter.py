#!/usr/bin/env python3
"""Validate the YAML frontmatter of SKILL.md files.

Hook mode (no arguments): reads a Claude Code PostToolUse event from stdin and
checks the file that was just written or edited, if it is a SKILL.md. On
problems it prints them to stderr and exits with 2, so the agent sees them and
fixes the file.

CLI mode: check-skill-frontmatter.py PATH...   (a PATH may be a directory, it is searched for SKILL.md)
"""
import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None


def check(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    m = re.match(r"---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|$)", text, re.S)
    if not m:
        return ["frontmatter missing: the file must start with '---' and the block must end with a closing '---'"]
    if yaml is None:
        return []
    try:
        data = yaml.safe_load(m.group(1))
    except yaml.YAMLError as e:
        hint = ""
        if "mapping values are not allowed" in str(e):
            hint = " (an unquoted value contains ': ' - quote the whole value or use a '>' block)"
        return [f"invalid YAML: {str(e).splitlines()[0]}{hint}",
                *[f"  {l}" for l in str(e).splitlines()[1:4]]]
    if not isinstance(data, dict):
        return ["frontmatter is not a YAML mapping"]
    problems = []
    for key in ("name", "description"):
        if not isinstance(data.get(key), str) or not data[key].strip():
            problems.append(f"'{key}' is missing or not a non-empty string")
    name = data.get("name")
    if isinstance(name, str):
        if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", name) or len(name) > 64:
            problems.append(f"name '{name}' must be lowercase letters, digits and hyphens, at most 64 characters")
        if name != path.parent.name:
            problems.append(f"name '{name}' differs from the folder name '{path.parent.name}'")
    desc = data.get("description")
    if isinstance(desc, str) and len(desc) > 1024:
        problems.append(f"description has {len(desc)} characters, the limit is 1024")
    return problems


def targets(args: list[str]) -> list[Path]:
    out = []
    for a in args:
        p = Path(a)
        out += sorted(p.rglob("SKILL.md")) if p.is_dir() else [p]
    return out


def main() -> int:
    if len(sys.argv) > 1:
        files = targets(sys.argv[1:])
    else:
        try:
            event = json.load(sys.stdin)
        except ValueError:
            return 0
        f = (event.get("tool_input") or {}).get("file_path") or ""
        if Path(f).name != "SKILL.md" or not Path(f).is_file():
            return 0
        files = [Path(f)]
    if yaml is None:
        print("check-skill-frontmatter: PyYAML not installed, only the '---' delimiters were checked (pip install pyyaml)", file=sys.stderr)
    bad = 0
    for p in files:
        problems = check(p)
        for line in problems:
            print(f"{p}: {line}", file=sys.stderr)
        bad += bool(problems)
    if len(sys.argv) > 1 and not bad:
        print(f"OK: {len(files)} SKILL.md file(s)")
    return 2 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
