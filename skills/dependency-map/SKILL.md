---
name: dependency-map
description: Find the dependencies between the artifacts of a codebase that a language tool such as jdeps, madge or an import graph does not see - names that must match between code, configuration, templates, data files and SQL (in Java, Python, PHP, Ruby, JavaScript and C code bases), classes, modules and functions named as strings, entry points in manifests, beans looked up by id, names built at run time (reflection, `import_module`, `const_get`, `require` with a variable, `dlsym`), URLs between templates and the routes that serve them, database tables shared by many files, and files that change together in Git, per commit and per ticket (change coupling), checked against what is already known to find hidden dependencies. It writes a typed edge list with the evidence and the confidence of every edge, and an evidence notebook that explains each kind (how it is searched, what breaks when its target changes, what would catch it) and illustrates what depends on what, next to the usual compiler-checked dependencies, plus a report of where names are built at run time (the radius there is only a lower bound). Deterministic, seconds to a minute, no LLM. Use for "hidden dependencies", "string dependencies", "connascence", "what does this class name in an XML or a database refer to", "what the dependency graph misses", "what depends on this beyond imports", or as input for a blast radius.
---

# Dependency Map

One question: **what depends on what, across all kinds of artifacts, including the dependencies a language tool cannot see?**

A language tool (`jdeps`, an import graph, `madge`) sees code that names other code the way the compiler understands it. In an old system much of the coupling lives elsewhere: in a name that has to be spelled the same in a class and an XML file, in a class name inside a string, in a bean id, a URL, a table, a key in a JSON file, or a function name that is turned into a class name at run time. Change one side and nothing fails to compile.

## The idea: connascence of name, across artifact boundaries

Connascence (Meilir Page-Jones) names the ways two pieces of code must change together. The statically findable ones are the **name** kind (two places must spell an identifier the same) and the **meaning** kind (a value must be interpreted the same). Both cross artifact boundaries: code, configuration, templates, data. The dynamic kinds (timing, execution order, identity) cannot be found without running the system, and this skill does not claim to.

## What it finds

The kinds are the same in every language; what differs is how a language spells them, and that lives in `scripts/ecosystems.py` (Java, Python, PHP, Ruby, JavaScript/TypeScript, C/C++). The script detects the languages of the repository (at least three code files) and applies their profiles; a language that is not there can be added as one more profile (regular expressions and two small functions), without touching the scanner. The Java and Spring rows (`xml-class`, `bean-ref`, `orm-relation`, `bean-lookup`, `prefix-class`) only produce edges where such files exist.

| Kind | An edge says | Found by | Confidence |
|---|---|---|---|
| `xml-class` | an XML file names a Java class (Spring bean, `web.xml` servlet/filter/listener, Hibernate mapping) | the attribute or element in the XML, with the line | verified by syntax |
| `bean-ref` | a bean's class depends on the class of the bean it references | the Spring XML tree | verified by syntax |
| `orm-relation` | a mapped class depends on the class of a mapped relation | the Hibernate mapping tree | verified by syntax |
| `url-link` | a template, script, test or class names a URL that a handler serves: it depends on that handler | the route declaration (`web.xml`, `@RequestMapping`, Flask/Django, Express, Sinatra, Slim/Laravel; routes declared in tests are ignored), then the URL as text (routes spelled with the slash); a single plain word named by many files is an ordinary word and gives no edge | heuristic |
| `data-table` / `table-defined-in` | a class, mapping or template uses a table; the table depends on the changelog or script that defines it | tables from Liquibase and SQL, then SQL keywords followed by the name | heuristic / verified by syntax |
| `string-class` | a class, module or function is named by its qualified name as text (Java `a.b.C`, Python `pkg.mod:func` in `pyproject.toml` or `from_object("x.Config")`, PHP `App\\Foo`, Ruby `Sinatra::Base`): reflection, JSON, TOML, properties, templates, seed data | exact match of the qualified name; in code only a whole string literal counts | verified by name |
| `file-name` | a string is the name of another file of the repository (a query file, a resource, an included template, a script in a workflow): the source depends on that file; a name shared by more than six files (`index.js`, `__init__.py`) says nothing and gives no edge; a directory part in the text (`include/footer.jsp`) picks the file first, and a name that still exists in several places (for example two modules) resolves to the nearest | the whole file name with its extension, in quotes | verified by name, heuristic where the name is shared |
| `key-link` | a rare key is spelled the same in code and in a data file (a message key, a query name, a value in a changelog's seed data), or in code and in a view (a request attribute, a parameter name): a contract between the two places; in a view the view depends on the code that sets the key | the same string in both places, rare in each; vendored libraries are skipped | heuristic |
| `bean-lookup` | code looks a bean up by its id (`getBean("x")`, `@Qualifier`, `@Resource`): it depends on the bean's class | exact match of the id | verified by name |
| `prefix-class` | code builds a class name at run time from a package it spells out: it depends on every class of that package | a package name as a string next to a `forName` or `loadClass` with a computed argument | heuristic |
| `dynamic-site` | code builds or looks up a name at run time: **its radius is a lower bound** (layer evidence) | `forName`, `getBean` with a computed argument (Java), `import_module`, `__import__`, `getattr`, `eval` (Python), `new $class`, `call_user_func` (PHP), `const_get`, `send`, `require` with a variable (Ruby), `require`/`import()`/`eval` with a variable (JavaScript), `dlopen`/`dlsym` (C) | verified by syntax, a hint for the human |
| `name-link` | an identifier declared in a few files (a class, a function, a property) is spelled the same in another artifact (a property in a JSP expression, a helper called from a template, a script name in a workflow, a bean id); in code of the same language only a whole string literal counts | the identifier as text; one-word and widespread names are left out | heuristic |
| `co-change` | two files changed together in Git often (layer evidence); the full analysis is `change_coupling.py` below | commits, mass commits left out | heuristic, no direction |

Two layers: **structure** edges say "source depends on target" and can feed any impact calculation such as a blast radius; **evidence** edges (`co-change`, `dynamic-site`) are leads for questions and prove nothing alone. Names shared so widely that an edge list would drown the rest (a bean name that 400 files spell) are reported as **hubs**, without edges.

## Set up for a repository

The defaults are neutral (`dependency-map.yaml` of the skill). What differs for one repository goes into an **override file** that holds only those keys, merged over the defaults with `--config <overrides.yaml>`: a vendored folder to exclude, a script library to ignore for URLs, keys or dynamic sites, a ticket pattern, a threshold. Do this before the first run:

1. **Look at the repository**: the languages and frameworks (the script prints the ecosystems it detects and the number of files in scope on stderr), the vendored and generated folders (`vendor/`, `node_modules/`, copied script libraries, minified or generated files), folders that are not the application (tooling, documentation tools), the ticket convention in the commit messages.
2. **Write the override** into the analysed repository (for example `notebooks/dependency-report/dependency-map.override.yaml`), not into the skill, and **show it to the human** with the scope before running: which languages, which files, which exclusions. This is the record of the settings used; keep it with the results.
3. **Pick the code-graph tool for the language** (see "The code-graph edge list") and say which one.

## Change coupling: where might more hide?

`scripts/change_coupling.py` asks of the history what the rules above did not find (oriented at ideas of Adam Tornhill). It computes the degree of coupling of every pair of files (shared changesets divided by the average number of changesets of the two), once per **commit** and once per **ticket** (the union of the files of all commits that carry a ticket number; the patterns for the numbers are in `dependency-map.yaml`, including GitHub's `(#123)` and `fixes #123`). Then it checks each coupled pair against everything known: the code graph and the *use* edges within a few steps, a URL, key or name, a table both use (also through code), or a shared dependency. A pair with none of these is a **candidate for a hidden dependency**: two files that must change together and that nothing connects.

```
uv run --no-project --with pyyaml python -I <skill dir>/scripts/change_coupling.py [--repo <path>] [--out <folder>] [--config <overrides.yaml>] [--code-edges <code-edges.csv>] [--edges <dependencies.csv>]
```

**Why do they change together? Patterns.** Coupling says that, never why. For every pair the report therefore checks a set of possible reasons and prints each with its evidence, as hypotheses a person can confirm or drop: a **clone** (the files are copies that evolved in parallel), a **shared vocabulary** (rare words in both: a concept, a column, a key or a template placeholder spelled out twice), a **naming family** (variants of one thing in one folder), a **vertical slice** (different layers sharing a concept: controller, view, query file, changelog), a **burst** (the shared changes fall into a short period: one event, not a standing link), **persistent** (they recur over a year or more), **one person** (one author made nearly all of them: habit, and the knowledge sits with them) and **bulk change** (large mechanical commits that say little). A pair that carries no label is the first to ask a person about. The labels are also how the rules of this skill improve: a recurring pattern among the hidden pairs shows which kind of dependency is still missing.

`--code-edges` is the edge list of the code graph (the usual dependencies, see "The code-graph edge list" below; this skill does not write it); without it the report says which pairs are known cannot be told. The result is `change-coupling.csv` and `change-coupling.md`: how many pairs are explained how strongly (direct, indirect, none), the hidden ones by file types, and the strongest leads with their ticket numbers. Coupling is evidence from history, never a proof: the same ticket, a release, a person or chance can explain it, and the report says so.

## The code-graph edge list (input, optional)

The usual dependencies are not found by this skill; a language tool finds them. The skill reads them as a CSV with the columns `source`, `target`, `kind`: one row per "source depends on target", file to file, with `kind` = `code` (module or class to module or class) or `template` (a view to the class it imports or to a page it includes or forwards to). **The agent picks the tool for the language** and says which: `jdeps -verbose:class -filter:none` for Java (the default filter drops every dependency inside one package), `madge --json` or `dependency-cruiser` for JavaScript and TypeScript, `grimp`, `pydeps` or a short `ast` script for Python, `deptrac` or the `use` lines for PHP, `require` lines or `packwerk` for Ruby, `#include` lines or `gcc -MM` for C. Any script that writes the file will do. It is used to tell the unusual dependencies from the usual ones in the report and to decide which coupled files are already explained. Without it, both still run and say what they cannot tell.

## The evidence notebook

The result is read in an **evidence notebook**, written with the `jupyter-notebook` skill (traceable, top to bottom, every step visible, assertions that fail loudly). The template is `report/dependency-report.ipynb`; the finished notebook lives in the repository that was analysed, as `notebooks/dependency-report/dependency-report.ipynb`, with its figures and tables in `output/` next to it.

It reads the files the scripts wrote (`dependencies.csv`, `change-coupling.csv`) and, for the usual dependencies, the code graph as an edge list (see "The code-graph edge list" below). Without the code graph it shows only the unusual dependencies, and says so. It contains:

- **One section per kind of dependency**, with the same four parts: *how it is found* (the search technique), *the dependency problem* (what breaks when the target is renamed, moved or deleted, and why nothing warns), *what catches it* (the compiler, the first request of a page, starting the application, a test on that path, a link check, or nothing) and *where it is weak*. Each section ends with the most depended-on targets and a random sample with the evidence line, for a person to check against the source. The usual dependencies (`code-graph`, `template-edge`) are described the same way, so the usual and the unusual are read side by side.
- **Illustrations of what depends on what:** the edges per kind, a matrix of artifact types, the layers with their arrows (one panel per way a kind carries a change: code, use, contract, data), and, for a chosen change (`FOCUS_FILES`), the files that depend on it sorted by how they fail and what would catch it. A last part shows how well the coupled pairs of files are explained, the patterns behind them and the hidden ones.
- **Code examples:** each kind shows real examples. Code cells (`show_example`, steered by `EXAMPLES_PER_KIND`, `EXAMPLE_SEED` and `CONTEXT_LINES` in the configuration) read the evidence line of a sampled edge and display source and target as numbered snippets with the hit marked, so the reader sees directly what depends on what. The dependents of the focus files and the hidden pairs get the same treatment. Examples come from code cells, never from text in markdown. This notebook is an *evidence notebook* in the sense of the `jupyter-notebook` skill (specific to one system, evidence, examples and interpretation); the scripts are the neutral, reusable part.
- **Checks that fail loudly:** the columns and kinds of the edge list, that every file endpoint is still a tracked file of the repository (an edge list from another commit is rejected), that no edge is lost in an aggregation, and that the written tables add up.

To produce it in a repository: run the scripts first (`dependencies.py`, `export_edges.py`, `change_coupling.py`), copy the template to `notebooks/dependency-report/`, set the paths and `FOCUS_FILES` in the first code cell, run `jupyter nbconvert --to notebook --execute --inplace dependency-report.ipynb` from that folder, and validate the file with `nbformat` as the `jupyter-notebook` skill describes. Look at every figure before handing it over; a notebook that fails validation is not delivered. Then make the **interpreted copy** that the `jupyter-notebook` skill describes: a timestamped copy with the repository state in its name, in which the important results get an assessment in marked light-blue cells (what the numbers show, how far to trust them, what to check next). The assessment is where the heuristic kinds, the sample precision and the hidden pairs are weighed for the reader; the original notebook stays free of it. It needs Jupyter, `pandas`, `matplotlib` and `numpy`; the notebook installs the Python packages in its own `%%bash` cell. Whether the generated `output/` is committed is the team's decision: it can be reproduced by running the notebook again.

## Principles

- **Every edge names its evidence** (file and line, or the commits) and its confidence. Never merge `verified` and `heuristic` into one number.
- **Heuristic edges are leads.** A table name or a URL in ordinary text can be a chance hit. Check a sample before relying on a kind, and say how big the sample was.
- **Say what is not covered**, every time: properties and message keys, what a computed name resolves to, annotation-based wiring, calls to other systems, live database data.
- **The kinds are the stable part, the patterns are the place to adapt.** `scripts/ecosystems.py` describes how each language spells a name, a route or a lookup; a language without a profile gets only the language-neutral kinds (file names, keys, tables, co-change), and the report says what it could not parse.
- **No LLM and no network.** An LLM can interpret the leads afterwards; it must not be the source of an edge.

## Procedure

1. **Set up for the repository** (see above): detect the ecosystems, write and show the override file, choose the code-graph tool. If a language is missing in `ecosystems.py`, say so; only the language-neutral kinds will work for it. Ask before running on a very large repository.
2. **Run the script** (`--repo`, default output `<repo>/temp/dependency-map`; look into an existing target folder before writing to it):

   ```
   uv run --no-project --with pyyaml python -I <skill dir>/scripts/dependencies.py [--repo <path>] [--out <folder>] [--config <overrides.yaml>]
   ```

3. **Read the report before the edges.** Per kind: how many edges, examples, the most depended-on targets; then the places where names are built at run time, the hubs, and what is not covered.
4. **Sample the heuristic kinds.** Draw a dozen edges per heuristic kind, check each against the source, and write down the share that held. Tune the thresholds in the override file where a kind is noisy, and record why.
5. **Ask the history what is still missing.** Write the code edges with the chosen tool, run `change_coupling.py`, and read the hidden pairs: each is a question for the people who know the code, and each cause found (a name convention, a shared table, a copy) can become a new rule for the patterns.
6. **Write the evidence notebook** from the template, run it and look at every figure (see the evidence notebook section).
7. **Hand over.** `dependencies.csv` is a plain edge list; whoever needs impact (for example a blast radius calculation) reads its `structure` edges and can filter by confidence. Point the human to the dynamic sites: there the radius cannot be trusted.

## Output

```
report/dependency-report.ipynb   the evidence notebook template (copy it to notebooks/dependency-report/ of the analysed repository)
dependencies.csv   source, target, kind, layer, confidence, evidence, weight   (one row per edge; tables appear as the node `table:<name>`, dynamic sites as `dynamic:<call>`)
dependencies.md    edges per kind, examples, most depended-on targets, where names are built at run time, name hubs, coverage, what is not covered
```

## Limits

- Six languages have a profile (Java, Python, PHP, Ruby, JavaScript/TypeScript, C/C++); others get only the language-neutral kinds. Framework conventions beyond the listed route styles (Rails resource routes, Django `reverse` names, dependency injection by type, Spring annotation scanning, `component-scan`) are not resolved.
- Where several apps live in one repository (a library with example apps), a URL declared in one can be matched by a test of another: `url-link` is a lead.
- A name is matched as text, not by meaning. `name-link` can connect two things that merely share a name.
- Ticket numbers cover only the commits that carry one (45% here); a pair below the thresholds, or a file with few revisions, is not judged.
- "Explained" has strengths: a table such as `study` that hundreds of classes use links almost anything, so an explanation through a table or a shared dependency is weak; the report counts direct and indirect explanations apart.
- A computed name is flagged, not resolved. `prefix-class` covers only the case where the package is spelled out in the same file.
- Seed data and changelogs in the repository are scanned; the live data of a database is not, so identifiers stored only at run time stay invisible.
- Generated or vendored files add noise unless they are excluded: check `scope.exclude` in the override file.
