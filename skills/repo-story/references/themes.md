# Design and themes

Articles and slides are **themeable**: colors and font live in a small CSS file (`assets/themes/<name>.css`) that `build.py` inserts into the template at `/*@@THEME@@*/`. The templates themselves contain no brand colors.

## Bundled themes
`default` (slate and amber, the default), `forest`, `plum`, `ocean`, `graphite`. Font: **Source Sans 3** (SIL Open Font License, static weights, lives in `assets/fonts/` and is embedded at build time, `OFL.txt` stays with it).

Use: `scripts/print-pdf.sh <folder> <name> forest` or `THEME=forest scripts/print-pdf.sh …`.

## Your own theme in one line
```
python3 scripts/make-theme.py mycompany "#2f5d50" "#c8a24a" --out ~/.config/repo-story/themes
```
Two colors are enough: **brand color** (dark: cover page, headings) and **accent color** (lines, markers, highlights). The script derives shades, text color, lines and an accent ink that has at least 4.5:1 contrast on white, and warns if the brand color is too light. With `--font "Family"` it uses your own font instead of Source Sans 3.

Search order: `./themes` (next to the source), `~/.config/repo-story/themes` (private, not in the skill), `<skill>/assets/themes`.

## Company font or brand (keep private)
**Never** put licensed fonts into the skill and never embed them in the HTML. Instead, a private theme in `~/.config/repo-story/themes/<name>.css` with its own `@font-face` (`local("…")` and `url("file:///path/to/font")`) and `--sans:` pointing to it. When printing, Chrome embeds only the glyphs used into the PDF. Then check with `pdffonts` that the font was really used (otherwise Chrome silently falls back to a system font).

## Variables of a theme
`--brand`, `--brand-75`, `--brand-25`, `--brand-soft` (main color and shades), `--accent`, `--accent-ink`, `--accent-soft`, `--on-brand` (text on dark background), `--ink`, `--muted`, `--line`, `--faint` (footer), `--screen-bg`, `--sans`, `--mono`. Charts read `brand`, `brand-25`, `muted`, `line`, `accent`, `accent-ink` from the theme (`THEME` in `charts.py`); own charts should do the same, never fixed colors.

## Check
Look at the contact sheet: text on dark background readable, accent areas not too pale, chart labels not overlapping. Light brand colors (e.g. yellow) work only as accent, not as main color.
