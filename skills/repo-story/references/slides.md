# Slides for social networks (PDF carousel)

In addition to the articles: the same story as slides. Two variants, both portrait **1080×1350 px (4:5)**, which reads best on a phone. Upload as PDF (most networks show it as a swipeable document).

| Variant | Slides | For | Template |
|---|---|---|---|
| **long** | 12 | Readers who really want the topic: acts, evidence, open points | `assets/slides/slides-long.src.html` |
| **short** | 6 | Quick post: numbers, punchline, pattern, questions, pointer to the article | `assets/slides/slides-short.src.html` |

Colors and font come from the theme (`references/themes.md`). The templates are **orientation, not a form**: they show the CSS, the slide types and the light/dark rhythm with neutral sample text. Change order, count and layout to fit the story, so that decks do not all look alike. Placeholders: `@@TITLE@@`, `@@PROJECT@@`, `@@KICKER@@` (title and footer); images are `cover.jpg`, `before.png`, `after.png`; charts are `chart-1` and `chart-2` in `charts.py`. Write the slides in the language of the linked article. A finished example is outlined in `references/example-photocraft.md`.

## Structure
**long (12):** title (dark, with picture) → summary (4 numbers) → first decisions → one act each with chart or picture (one topic each, e.g. breadth, robustness, fidelity, community) → instructions for agents (AGENTS.md or similar) → the pattern (dark) → what is open → questions to the reader → read more (dark, sources).
**short (6):** title → summary (4 numbers) → the punchline with quote and one chart → the pattern (dark) → questions → read more (dark).

Keep the order of slide types: the light/dark alternation sets the rhythm.

## Rules
1. **One message per slide**, headline as a sentence. Running text at most three lines; everything else belongs in the article.
2. **The same numbers as in the article**, from the measurements, never from memory. Never drop the "What is open" slide (long); in short, the honest status is on the last slide.
3. **Name the project right on the cover slide** (name in the kicker, subtitle says in half a sentence what it is), so it is clear at first glance what this is about.
4. **Replace jargon or explain it in half a sentence** (fuzz test: "calls every command with hostile parameters").
5. **Source slide at the end**: basis, snapshot, note "the authors' intent is our interpretation", who measured and wrote. **Credit the images:** say which come from the project's repository (with path and licence) and which you rendered yourself.
6. The slide count is in `data-t` of each `<section>`; when changing the count, adjust all `data-t`.
7. Language like the article that is linked. Check the slides for overflow into the footer after building and shorten sentences. Chart labels (`goal`, `old`, `new`, ...) come from the chart code in `charts.py`: set them in the language of the slides.

## Build
Name every output after the project: copy the templates under `<project>-slides-...` so that the PDFs are called `<project>-slides-long.pdf` and so on, not just `slides-long.pdf`.
```
P=<project>   # repo or project name, lower case
mkdir slides && cp assets/build.py assets/slides/charts.py slides/   # plus images
for v in long short; do cp assets/slides/slides-$v.src.html slides/$P-slides-$v.src.html; done
scripts/print-pdf.sh slides $P-slides-long
scripts/print-pdf.sh slides $P-slides-short
scripts/print-pdf.sh slides $P-slides-long-en forest   # third argument = theme
```
`print-pdf.sh` works unchanged: the page size comes from `@page{size:1080px 1350px}` in the template. Charts work as in the article via `{{CHART:name}}` and `charts.py` (example `assets/slides/charts.py`, colors from the theme); the SVG labels in the slides are set to 14.5 px via CSS (`.chart svg text`), check wider charts.

## Check
`pdfinfo` (page count = 12 or 6, page size 810×1013 pt), `pdffonts` (font embedded?), then a **contact sheet** (`pdftoppm -r 40`, mount pages side by side). Typical errors: text runs into the footer (shorten the slide or reduce the font, do not enlarge the page), teal text on a dark background (invisible), chart labels overlap. Also check that the title slide says what the project is.
