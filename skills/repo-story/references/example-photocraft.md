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
