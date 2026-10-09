#!/bin/bash
# Builds an article and prints it as PDF (headless Chrome, Linux/WSL: Playwright Chromium or system Chrome).
# Usage: [THEME=name] print-pdf.sh <folder> <name> [theme]   (expects <name>.src.html and build.py in the folder; themes: see assets/themes)
# Then check: pdfinfo, pdffonts (font embedded?), contact sheet via pdftoppm.
set -euo pipefail
export REPO_STORY_ASSETS="$(cd "$(dirname "$0")/../assets" && pwd)"  # the skill's themes and fonts, even if build.py was copied
D=${1:?folder}; N=${2:?name}; cd "$D"
THEME="${3:-${THEME:-default}}" python3 build.py "$N"
CH=$(command -v google-chrome || command -v chromium || ls -d "$HOME"/.cache/ms-playwright/chromium-*/chrome-linux*/chrome 2>/dev/null | tail -1 || true)
[ -n "$CH" ] || { echo "Chrome/Chromium not found." >&2; exit 1; }
"$CH" --headless=new --no-sandbox --disable-gpu --no-pdf-header-footer --print-to-pdf="$PWD/$N.pdf" "file://$PWD/$N.html" 2>&1 | grep -i written || true
pdfinfo "$N.pdf" | grep -E "Pages|Page size"
pdffonts "$N.pdf" | head -6
