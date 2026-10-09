---
name: repo-story
description: Software archaeology for any Git repo (Rust, Java/Maven/Gradle, Node, Go, Python). Checks whether the development history went the way the log tells it - builds every commit in an isolated container, tests key commits, re-measures claims from commit messages, finds jumps by bisection. Turns the results into designed PDF articles (measurement and story) and social-network slides as PDF (long 12 slides, short 6 slides), plus a post text. Use this skill for "replay the history", "does the git history hold up", "build every commit", "repo archaeology", "article / slides about a project", "how was X built", "project story from the git log", "slides / carousel / social media post about the project", or whenever a report, article or slides should come out of a repo's history. Also for questions about how people work with AI agents in a repo (evaluating AGENTS.md, CLAUDE.md, README, commit trailers).
---

# Repo-Story (repo archaeology)

Turn a project's Git history into three things: **measured facts** (does the story hold up?), **readable articles** (story plus method, numbers in the margin) and **slides** for social networks. Language-independent; Rust, Java (Maven, Gradle), Node, Go and Python are prepared. Created while evaluating PhotoCraft (example: `references/example-photocraft.md`).

## Ask first (at most four questions, otherwise use defaults)
1. Which repo, which branch, which ecosystem? (Check the build file in the repo: `pom.xml` -> maven, `build.gradle*` -> gradle, `Cargo.toml` -> cargo, `package.json` -> npm, `go.mod` -> go.)
2. May the build use the network? (Almost always needed for Java/Node: then a container with network, without credentials.)
3. Which design (theme, colors; default `default`)? Where do the results go, and is it one article or two? Tone: factual or narrative? Slides as well (long 12 or short 6 slides, or both)?
4. Delete the container afterwards? Default: no, ask at the end.

## Workflow in steps 0 to 8
Details: `references/method.md`. Commands and pitfalls per language: `references/ecosystems.md`. Keep the order, above all step 0.

0. **Safety first.** Third-party code only in the container: builds run scripts, plugins and dependency code. Template `assets/devcontainer/` (Dockerfile per ecosystem: Rust, Java, Node, Go, Python); `replay.sh` and `bisect-metric.sh` refuse to run outside a container. The coding agent that drives the skill runs inside that container too, so the container must ship with it: install your agent in the image (add a line to the Dockerfile or a devcontainer feature) and give it access at runtime (login or environment variable), never baked into the image. Do not mount the original, disable push, no credentials, commit nothing, never silently re-resolve dependencies.
1. **Replay.** `ECOSYSTEM=<eco> scripts/replay.sh <clone> <results>`: check out and build every first-parent commit, status in CSV, resumable.
2. **Plausibility.** Verify short "ok" times with a cold sample, second pass with tests, format/lint, read numbers from commit messages per commit and re-measure them.
3. **Read third-party code.** `scripts/review-build-scripts.sh <clone> <eco>`: read all historical build scripts/configurations before running them.
4. **Deepen key commits.** 15 to 20 states with tests and project-specific metrics. Verify SHAs via `git log --grep`.
5. **Find jumps.** `scripts/bisect-metric.sh`. If there is an oracle (reference output), measure old states against it.
6. **Write.** `references/storytelling.md`; build and print with `scripts/print-pdf.sh`, template in `assets/`.
7. **Slides** (on request, after the articles, same numbers): `references/slides.md`; templates `assets/slides/slides-long.src.html` (long, 12 slides) and `assets/slides/slides-short.src.html` (short, 6 slides); format 1080x1350.
8. **Social-media post** for article and slides (on request): `references/social-post.md` (guide, text template, rules). Never post it yourself.

## Hard rules
- **Measuring means: give value, command, state.** Write authors' intentions as fact only where they appear in commit messages or docs, otherwise mark them as "our reading".
- **Report toolchain deviation** (today's compiler/JDK, not the one of that day). Measuring old states against today's test data tells what the code could do, not what the authors saw.
- **Not buildable != broken.** Report `dep_fail` (dependency gone, lock does not match) separately from `fail`. Especially to be expected with Java without a lock file.
- **Commit trailers prove involvement, their absence proves nothing.** Squash commits count trailers multiple times: count per commit.
- **Do not silently repeat invalid runs.** Discard, name the cause, measure again, keep the old run for documentation only.
- **README and docs may lag behind.** That is material, not a measurement error.

## Storing results
`results/` next to the clone: `results.csv`, `logs/`, `variant-b.csv`, `scripts/` (with README: what ran as a script, what by hand), `report.md`, `cases.md`, one folder per article with `*.src.html`, `build.py`, PDF; slides in `slides/`. File names start with the **repo name** and give type, variant and language (`<repo>-article-en.pdf`, `<repo>-measurement-en.pdf`, `<repo>-slides-long-en.pdf`, `<repo>-slides-short-en.pdf`), never a bare `article.pdf` or `slides.pdf`, so a loose file is unambiguous outside its folder. `print-pdf.sh` takes the name from `<name>.src.html`: name the source this way from the start.

## Building an article (short guide)
1. Create a folder, copy `assets/build.py` and `assets/article-template.src.html` into it, rename the template to `<name>.src.html`, replace the `@@...@@` placeholders (`@@TITLE@@`, `@@AUTHOR@@`, `@@DATE@@`, `@@PROJECT@@`, `@@KICKER@@`). **Design:** choose a theme (`default`, `forest`, `plum`, `ocean`, `graphite` or your own via `scripts/make-theme.py`), see `references/themes.md`.
2. Put images next to the source (`{{IMG:file.png}}`, JPG is embedded appropriately). Charts in `charts.py` as `CHARTS = {"name": fn}` with `line_chart()`.
3. Check with `pdffonts` that the font is embedded in the PDF. Source Sans 3 (OFL) is bundled. Licensed company fonts only in a private theme under `~/.config/repo-story/themes`, never in the skill.
4. `scripts/print-pdf.sh <folder> <name> [theme]` builds and prints. Then look at a contact sheet (`pdftoppm -r 40`, montage the pages into a grid), fix gaps and orphaned headings, print again.
5. Tell the user the path, under WSL also the Windows form (`wslpath -w`).
