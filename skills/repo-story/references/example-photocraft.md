# Example: PhotoCraft (Rust, 516 commits, 9 days)

For orientation on what a finished result looks like. The concrete commands and metrics do not transfer.

- **Environment:** container `photocraft-dev`, Rust 1.99, lavapipe as software Vulkan, volumes for target and registry (the registry volume belonged to root: first run invalid, own `CARGO_HOME`).
- **Replay:** 510 first-parent commits, `cargo check --workspace --locked`: all green except 1 lock mismatch. With `--all-targets` 7 red commits in 3 stretches, `cargo fmt --check` 155 red commits.
- **Plausibility:** 148 commits "ok" in 0 to 1 s; cold sample of 10 with an empty target: 41 to 56 s, also green.
- **Third-party code:** 4 `build.rs` paths in 5 versions read (no process spawn, no network); build scripts of 53 third-party crates ran unreviewed.
- **Key commits:** 20 states with tests (971 to 3,974), fuzz test `panic_hunt`, layer check `xtask layers`, Clippy, corpus tests.
- **Metrics from the repo:** the checked-in parity number (menu items with a live command) read per commit, re-measured at 20 points.
- **Oracle:** Photoshop's own rendering of 258 PSD files, tolerance 2/255. Fidelity curve 70 -> 133. Jump 74 -> 128 narrowed to one commit by bisection (7 builds) (text anti-aliasing in its own gamma space).
- **Cases:** community batch on 5 Oct (eight PRs in two minutes, repair commit afterwards), fidelity jump, `panic_hunt` finds a 4 TB allocation.
- **Finding:** The code never broke the compiler; what was red were tests, formatting, lints. Commit messages were reliable; README numbers lagged behind.
- **Results:** `results.csv`, `variant-b.csv`, `report.md`, `cases.md`, articles "Nine days, 516 commits" and "How PhotoCraft came to be".

## Slides of the example (long, 12)
1. Cover: "An editor that agents can operate too", one sentence on what PhotoCraft is and its repo link, demo picture.
2. Short version: 9 days, 516 commits (307 with a Claude co-author), 817 commands, 3,974 tests; all 510 rebuilt commits compile.
3. Act 1, scaffold: hour three, 42,241 lines, four decisions (one command list, thin UI, perception for the agent, JSON and MCP servers).
4. Act 2, breadth: menu parity chart 518 to 625 of 625, quote "depth/fidelity remain".
5. Act 3, robustness: rule 9 "no input may crash a command", fuzz test finds a 4 TB allocation.
6. Act 4, fidelity: 258 Photoshop files as oracle, chart 74 to 128 in one commit, grey 120 instead of 125.
7. Act 5, community: eight PRs in two minutes, before/after pictures of the menu.
8. The manual: what AGENTS.md really contains (mechanics, closing list, dev log, parallel agents), compiler as guard.
9. The pattern (dark): crash -> fuzz test, "looks right" -> pixel oracle, red formatting -> CI step, ...
10. Honest status: 133 of 258 files within tolerance; README says 1,700 tests, we measured 3,974.
11. Five questions for your own product.
12. Read more and sources (dark).
