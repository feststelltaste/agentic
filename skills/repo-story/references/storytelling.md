# Writing the articles: what the user wanted

Two articles, not one. They came out of feedback ("too boring", "it doesn't say what PhotoCraft is").

## Article A: Measurement ("Nine days, 516 commits")
For readers who want evidence. Structure: facts bar, What did we measure, three acts (breadth, robustness, fidelity) with one chart each, community, who writes, **How we measured** (container, five check layers, bisection, oracle, limits), What remains, What we do not know.

## Article B: Story and approach ("An editor that agents can use too")
For readers who want to be entertained. **Tells the story and the way of working; commits and builds only on the margin** (`aside.note`).
Structure: standfirst → **What is <Project>?** (box + picture) → acts → instructions for agents (AGENTS.md) → How to work with agents when you do not trust them blindly → What we take away (questions for the readers).
Dramaturgy: every time something went wrong, the project built a check instead of a warning. That is the punchline.
Best moments (by instinct): a commit that reports "100 %" and 16 seconds later says what the number does not mean; a fuzz test that finds a terabyte allocation; five gray levels of deviation that only the oracle sees.

## Rules from the feedback
1. **Always say what the project is**, even if the reader "should know it": what, what for, built with what, license, maturity, picture. One box plus figure 0.
2. **Explain or replace jargon.** "Crate" → "building block (called a crate in Rust)". Clippy, lockfile, oracle, parity, bisection, fuzz: explain briefly on first use (a margin note is enough).
3. **Numbers and commit numbers go in the margin**, not in the running text of the story.
4. **Stay honest:** what was not measured goes in a box "What we do not know". Mark intentions as interpretation. Show outdated numbers in the README as a margin note.
5. **File names speak:** `photocraft-story.pdf`, `photocraft-measurement.pdf`, not `article2.pdf`.
6. **The language of the results follows the project/user**; replies to the user follow the language of the session.
7. Check with tools, do not guess: render the PDF, look at the pages as a contact sheet (`pdftoppm -r 40`, combine images into a grid), remove forced page breaks when gaps appear, keep headings away from the page bottom (`h3{break-after:avoid}`).

## Design
Template in `assets/` (A4, cover page, margin column, facts bar, boxes, pull quote, figures, SVG charts). Colors and font come from a **theme** (default `default`, Source Sans 3 bundled); own colors via `scripts/make-theme.py`, licensed fonts only privately: see `references/themes.md`.
