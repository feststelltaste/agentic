# Ecosystems: what changes per language

The method stays the same, only these cells change. `scripts/replay.sh` has presets (`ECOSYSTEM=...`), everything overridable via `BUILD_CMD`, `BUILD_FILES`, `DEP_FAIL_RE`.

| | Rust (cargo) | **Java Maven** | **Java Gradle** | Node (npm) | Go | Python |
|---|---|---|---|---|---|---|
| Build file | `Cargo.toml` | `pom.xml` | `build.gradle(.kts)`, `settings.gradle*` | `package.json` | `go.mod` | `pyproject.toml`, `setup.py` |
| "Does it build?" | `cargo check --workspace --locked` | `mvn -B -q -DskipTests test-compile` | `./gradlew --no-daemon -q testClasses` | `npm ci --ignore-scripts && npm run build` | `go build ./...` | `python -m compileall` |
| With tests (step 2b) | `--all-targets` | `mvn -B verify` (without `-DskipTests`) | `./gradlew test` | `npm test` | `go vet ./... && go test ./...` | `pytest -x` |
| Format/lint | `cargo fmt --check`, `clippy -D warnings` | `spotless:check`, `checkstyle:check` (only if configured) | `spotlessCheck`, `checkstyleMain` | `prettier --check`, `eslint` | `gofmt -l`, `go vet` | `ruff`, `black --check` |
| Lock/reproducibility | `Cargo.lock` + `--locked` | **no lock file**: versions are in the POM, SNAPSHOT/range versions and mutable repos make old states unreproducible | optional `gradle.lockfile` (dependency locking) | `package-lock.json` + `npm ci` | `go.sum` | `requirements.txt`/`poetry.lock` |
| Code execution during build | `build.rs`, proc macros, dependencies | **Maven plugins** (exec, antrun, gmavenplus), annotation processors, wrapper download | **Build scripts (Groovy/Kotlin), buildSrc, init scripts, wrapper download** | `postinstall` scripts (off with `--ignore-scripts`) | `go:generate` (does not run during build) | `setup.py` |
| Network needed? | only crate download | **yes** (Maven Central, plugin repos) | **yes** (Gradle distribution, plugin portal) | yes (registry) | yes (proxy) | yes (PyPI) |
| Dep-failure status | lock does not match | artifact not resolvable (deleted snapshots, dead repos) | like Maven | lock/ERESOLVE | go.sum missing | - |
| Toolchain deviation | `rust-version`, edition | **JDK version** (`maven.compiler.release`, `toolchains`), several JDKs in the image | JDK + Gradle version (wrapper pins) | Node version (`.nvmrc`, `engines`) | `go` line in `go.mod` | Python version |

## Java specifics

- **Security is harder than with Rust.** Maven plugins and Gradle scripts are arbitrary code that needs network access. A network-less container does not work. Therefore: no host mount except the working folder, **no credentials** (no `~/.m2/settings.xml`, no host `~/.gradle/gradle.properties`, no tokens), `--cap-drop=ALL`, if possible network access only to Maven Central/Gradle portal (proxy or firewall). Step 3 (`scripts/review-build-scripts.sh <repo> maven|gradle`) reads all historical POMs/Gradle files for `exec`, `antrun`, foreign `<repository>` entries, `distributionUrl`, `curl`/`wget`.
- **Wrapper:** `mvnw`/`gradlew` download a distribution from the network, the URL comes from the history. Check the wrapper URL per commit before running it.
- **Old states are often no longer buildable**, not because the code was broken, but because artifacts disappeared (snapshot repos, JCenter, http repos that Maven has blocked since 3.8.1). That is what the `dep_fail` status is for. Do not count it as "code was red"; report it separately. Expect and explain this up front in the report.
- **JDK per commit:** if an old state only runs with JDK 8/11, switch the JDK during the run (`JAVA_HOME`) and note it in the CSV. Otherwise code and toolchain failures get mixed.
- **Multi-module:** `-q` hides reactor output. For "which module broke", keep the log without `-q` or use `--fail-at-end` plus `-pl`/`-am`.
- **Metrics you can measure:** test count from Surefire reports (`target/surefire-reports/*.xml`, sum of `tests=`), coverage (JaCoCo), module count, lines per module, dependency count (`mvn dependency:list`), architecture rules (ArchUnit tests). For key commits, decide before the run what is compared.
- **Oracles in Java:** reference output of the original, golden-file or approval tests, compatibility suites (TCK), benchmarks (JMH). Without an oracle, "is the number in the commit message right?" stays limited to test count and build time.

## Adding a new ecosystem
`ECOSYSTEM=custom BUILD_FILES="..." BUILD_CMD="..." DEP_FAIL_RE="..." scripts/replay.sh ...` and add a column to this table. Always clarify: Is there a lock file? What executes code during the build? Does the build need network? Which toolchain version belongs to which commit?
