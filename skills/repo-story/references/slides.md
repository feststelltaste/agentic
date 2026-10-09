# Slides for social networks (PDF carousel)

In addition to the articles: the same story as slides. Two variants, both portrait **1080×1350 px (4:5)**, which reads best on a phone. Upload as PDF (most networks show it as a swipeable document).

| Variant | Slides | For | Template |
|---|---|---|---|
| **long** | 12 | Readers who really want the topic: acts, evidence, open points | `assets/slides/slides-lang.src.html` |
| **short** | 6 | Quick post: numbers, punchline, pattern, questions, pointer to the article | `assets/slides/slides-kurz.src.html` |

Colors and font come from the theme (`references/themes.md`). The templates are the finished PhotoCraft example, **each variant in English and German** (`slides-lang.src.html`, `slides-kurz.src.html`, plus the German-language example variants `slides-lang-de.src.html`, `slides-kurz-de.src.html`). Choose the language by article and audience, build both on request. Replace the content, **keep the CSS and slide types**.

## Structure
**long (12):** title (dark, with picture) → summary (4 numbers) → scaffold/decisions → one act each with chart or picture (breadth, robustness, fidelity, community) → instructions for agents (AGENTS.md or similar) → the pattern (dark) → what is open → questions to the reader → read more (dark, sources).
**short (6):** title → summary (4 numbers) → the punchline with quote and one chart → the pattern (dark) → questions → read more (dark).

Keep the order of slide types: the light/dark alternation sets the rhythm.

## Rules
1. **One message per slide**, headline as a sentence. Running text at most three lines; everything else belongs in the article.
2. **The same numbers as in the article**, from the measurements, never from memory. Never drop the "What is open" slide (long); in short, the honest status is on the last slide.
3. **Explain the project** if it is not well known: the title slide says what it is.
4. **Replace jargon or explain it in half a sentence** (fuzz test: "calls every command with hostile parameters").
5. **Source slide at the end**: basis, snapshot, note "the authors' intent is our interpretation", who measured and wrote.
6. The slide count is in `data-t` of each `<section>`; when changing the count, adjust all `data-t`.
7. Language like the article that is linked. **German texts are about 15 % longer**: check those slides for overflow into the footer after building and shorten sentences (the slides "scaffold", "AGENTS.md", "What is open" were the candidates). Chart labels (`all 258`, `before`, ...) come from the chart code: for the German version use the German labels (the `_de` chart functions), not the English ones.

## Build
```
mkdir slides && cp assets/build.py assets/slides/charts.py assets/slides/slides-*.src.html slides/   # plus images
scripts/print-pdf.sh slides slides-lang
scripts/print-pdf.sh slides slides-kurz
scripts/print-pdf.sh slides slides-lang-de forest   # third argument = theme, and slides-kurz-de
```
`print-pdf.sh` works unchanged: the page size comes from `@page{size:1080px 1350px}` in the template. Charts work as in the article via `{{CHART:name}}` and `charts.py` (example `assets/slides/charts.py`, colors from the theme); the SVG labels in the slides are set to 14.5 px via CSS (`.chart svg text`), check wider charts.

## Check
`pdfinfo` (page count = 12 or 6, page size 810×1013 pt), `pdffonts` (font embedded?), then a **contact sheet** (`pdftoppm -r 40`, mount pages side by side). Typical errors: text runs into the footer (shorten the slide or reduce the font, do not enlarge the page), teal text on a dark background (invisible), chart labels overlap.
