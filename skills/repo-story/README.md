# repo-story

A skill for **repo archaeology**: rebuild a project's git history commit by commit in an isolated container, re-measure what the commit messages claim, find the jumps by bisection, and turn the result into

- a designed **PDF article** (measurement and story),
- **Slides for social networks** (carousel) as PDF, 12 or 6 pages, 1080×1350, in English and German (the `-de` templates are German-language example variants).

Ecosystems prepared: Rust, Java (Maven/Gradle), Node, Go, Python. Developed on the open-source project PhotoCraft (see `references/example-photocraft.md`).

## Use
Copy the folder to where your agent loads skills (e.g. `~/.claude/skills/repo-story/` or `.claude/skills/` in a repo) and ask, e.g. "replay the history of this repo and write an article and slides". Output language follows your request.

Needs: bash, git, Python 3, a container runtime (e.g. Docker) and Chrome or Chromium and poppler (`pdfinfo`, `pdffonts`, `pdftoppm`) for the PDF step (see `scripts/print-pdf.sh`).

## Design
Neutral default theme, bundled font (Source Sans 3, SIL OFL). Make your own colors in one line:

    python3 scripts/make-theme.py mycompany "#2f5d50" "#c8a24a" --out ~/.config/repo-story/themes
    scripts/print-pdf.sh <folder> <name> mycompany

Details: `references/themes.md`.

## Safety
Builds run foreign code. The skill builds only in a container (`assets/devcontainer/`), without credentials, with push disabled, and reads build scripts before running them. Do not skip that step.

## License
Skill files: use freely. `assets/fonts/`: SIL Open Font License 1.1, see `assets/fonts/OFL.txt`.
