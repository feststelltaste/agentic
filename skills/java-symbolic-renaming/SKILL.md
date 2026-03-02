---
name: java-symbolic-renaming
description: Rename or improve a Java identifier using symbolic code transformation tools, especially for large-scale renames across the codebase. Trigger when the user wants to rename a symbol, improve a name, asks "what should I call this", or wants naming suggestions for Java code.
---

# Improve Naming

## Workflow

### 1. Detect available tools (run in parallel)
- **Language server**: check if an LSP MCP tool exposing `rename_symbol` (or equivalent) is available
- **Serena**: check if Serena's `rename_symbol` is available as an MCP tool (fallback if no direct LSP)
- **OpenRewrite**: grep `pom.xml` / `build.gradle` for `openrewrite`, or look for `rewrite.yml`
- **ast-grep**: `which ast-grep`

### 2. Find and analyze the symbol
- Use language server reference lookup if available, Serena `find_referencing_symbols` as fallback, otherwise Grep
- Read the declaration and surrounding class/method context
- Read 2-3 call sites to understand intent

### 3. Classify the identifier

| Type | Risk | Notes |
|---|---|---|
| Local variable / parameter | Low | Scoped to method body |
| Private field / method | Medium | Check for reflection usage |
| Package-private method | Medium | Grep the package |
| Public / protected method | High | All callers + subclass overrides + interface impls |
| Class / Interface | High | All files, imports, config, strings |
| Static constant (`static final`) | Medium | May appear in annotations or serialized data |

If the rename is **High risk and no LSP tool or Serena is available**, or if you discover the rename has cascading
dependencies (many callers, multiple modules, interface + implementations), suggest using the
**mikado-graph skill** to plan the work incrementally before touching any code.

### 4. Propose alternatives

Suggest 2-3 names. For each, explain why it is clearer. Apply Java conventions:
- Methods: verb or verb-noun (`calculateTotal`, `isValid`, `findById`)
- Fields / variables: noun or noun-phrase (`userCount`, `orderId`)
- Classes: PascalCase noun (`OrderProcessor`, `PaymentService`)
- Constants: `UPPER_SNAKE_CASE`
- Booleans: `is`, `has`, `can`, `should` prefix

Wait for user to pick a name before proceeding.

### 5. Generate rename artifact for review

Before executing anything, generate the rename artifact and present it to the user for review:

| Tool | Artifact to generate |
|---|---|
| Language server | Show list of all files/symbols the LSP rename will touch, then ask to confirm before executing |
| Serena | Show list of all files/symbols `find_referencing_symbols` will touch, then ask to confirm before calling `rename_symbol` |
| OpenRewrite | Write `rewrite.yml` to project root and show its contents |
| ast-grep | Write `rename.yml` and show the `ast-grep` command to run |
| None | Write `rename.sh` with scoped `find + sed` commands - see [REFERENCE.md](REFERENCE.md#rename-script) |

Wait for user to confirm the artifact looks correct before proceeding.

### 6. Execute rename

Run the artifact approved in step 5:

| Tool | Command |
|---|---|
| Language server | Call LSP rename via MCP tool |
| Serena | Call `rename_symbol` |
| OpenRewrite (Maven) | `./mvnw -U org.openrewrite.maven:rewrite-maven-plugin:run -Drewrite.recipeArtifactCoordinates=org.openrewrite:rewrite-java:LATEST -DactiveRecipes=RenameSymbol` |
| OpenRewrite (Gradle) | `./gradlew rewriteRun` |
| ast-grep | `ast-grep scan --rule rename.yml --rewrite src/` |
| None | `bash rename.sh` |

**Tool selection rules (priority order):**
1. Language server (LSP MCP tool) — most accurate, IDE-grade rename
2. Serena — wraps LSP, use when no direct LSP tool is available
3. OpenRewrite — for public methods / classes when no LSP tool is available (AST-aware, handles imports)
4. ast-grep — sufficient for local variables / parameters
5. Manual `rename.sh` — last resort
- When risk is High and no LSP tool or Serena is available, warn the user to review the diff carefully before committing

### 7. Update comments and Javadoc

No tool (including Serena) reliably renames identifiers inside comments. Always do this step explicitly:
- Grep for the old name in comments and Javadoc across the codebase
- Update structured Javadoc tags: `@param oldName`, `{@link OldClass#oldMethod()}`, `{@code oldName}`, `@see`
- Update free-text inline comments that mention the identifier by name
- See [REFERENCE.md](REFERENCE.md#comments-and-javadoc) for grep patterns
