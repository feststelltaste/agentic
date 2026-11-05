#!/usr/bin/env python3
"""The code graph of a C# repository as an edge list, for change_coupling.py --code-edges and the evidence notebook.

C# does not tie a type to a file (a namespace is not a folder, a file can hold several types, a `partial` type spans several files), so an
import graph says little. This script reads what the compiler would resolve, approximately: every type a .cs file declares (with its
namespace), then every identifier in the other files that is the name of such a type. A type counts only where its namespace is visible
(the file's own and parent namespaces, `using`, `global using`, `<Using Include>` in a project file); a name whose namespace the file cannot
see is a property, an enum member or a variable and is left out. A name declared in several visible namespaces gives an edge to each, marked
`ambiguous`; a name written with its namespace is resolved exactly. A member after a dot is not a type. Comments and string literals are
skipped. It is a heuristic, not Roslyn: a local variable named like a visible type and `using` aliases are not told apart, and the SDK's
implicit usings (System.*) are not read because they name no type of the repository; the summary line counts what was left out.

  python3 -I <skill dir>/scripts/code_edges_csharp.py [--repo <path>] [--out <folder>] [--config <overrides.yaml>]
Writes code-edges.csv (source,target,kind,weight,resolution). Needs PyYAML (for the scope in dependency-map.yaml). No LLM, no build.
"""
import argparse, collections, csv, re, subprocess, sys
from pathlib import Path

try:
    import yaml  # noqa: F401  (settings needs it)
except ImportError:
    sys.exit("Missing dependency (yaml). Run it with:\n  uv run --no-project --with pyyaml python -I " + str(Path(__file__)))

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ecosystems as eco
import settings

# comments, then strings (raw """...""", verbatim @"..." with "" escapes, regular "..." and char '.'), then identifiers
TOKENS = re.compile(r'//[^\n]*|/\*.*?\*/|\$*"""(?:.|\n)*?"""|[$@]{1,2}"(?:[^"]|"")*"|\$?"(?:\\.|[^"\\\n])*"|\'(?:\\.|[^\'\\\n])+\'|@?[A-Za-z_]\w*(?:\s*\.\s*[A-Za-z_]\w*)*', re.S)
USING = re.compile(r"^\s*(?:global\s+)?using\s+(?:static\s+)?([\w.]+)\s*;", re.M)
GLOBAL_USING = re.compile(r"^\s*global\s+using\s+(?:static\s+)?([\w.]+)\s*;", re.M)


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, errors="replace").stdout


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", default=".")
    ap.add_argument("--out", default="temp/dependency-map")
    ap.add_argument("--config", default=None, help="override file merged over dependency-map.yaml (scope.exclude is used)")
    a = ap.parse_args()
    repo, out = Path(a.repo).resolve(), Path(a.out)
    cfg = settings.load(a.config)
    excl = [re.compile(x) for x in cfg["scope"]["exclude"]]
    files = [f for f in git(repo, "ls-files", "-z").split("\0") if f.endswith(".cs") and not any(x.search(f) for x in excl)]
    if not files:
        sys.exit("No .cs files in scope.")
    texts = {f: (repo / f).read_text(errors="replace") for f in files if (repo / f).is_file()}

    declared = collections.defaultdict(set)             # simple type name -> {(namespace, file)}
    for f, t in texts.items():
        for full, _ in eco._csharp(f, t):
            ns, _, name = full.rpartition(".")
            declared[name].add((ns, f))

    full_names = {f"{ns}.{name}": (ns, g) for name, d in declared.items() for ns, g in d if ns}
    global_usings = {m.group(1) for t in texts.values() for m in GLOBAL_USING.finditer(t)}
    for proj in (f for f in git(repo, "ls-files", "-z").split("\0") if f.endswith((".csproj", ".props"))):   # <Using Include="Ns"/> is a global using too
        global_usings |= set(re.findall(r'<Using\s+Include\s*=\s*"([\w.]+)"', (repo / proj).read_text(errors="replace")))
    edges, report = collections.Counter(), collections.Counter()
    resolution = {}
    for f, t in texts.items():
        own_ns = {m.group(1) for m in eco.CS_NAMESPACE.finditer(t)}
        visible = own_ns | global_usings | {m.group(1) for m in USING.finditer(t)}
        visible |= {ns.rsplit(".", i)[0] for ns in own_ns for i in range(1, ns.count(".") + 1)}   # parent namespaces are in scope too
        visible.add("")                                  # the global namespace
        counts = collections.Counter()
        for m in TOKENS.finditer(t):
            tok = m.group(0).lstrip("@")
            if not (tok[0].isalpha() or tok[0] == "_"):
                continue                                 # a comment or a string
            if t[:m.start()].rstrip()[-1:] == ".":
                continue                                 # a member after a call or an index: `GetExecutingAssembly().Location`
            parts = re.split(r"\s*\.\s*", tok)          # a dotted chain: only its head names a type (`Assembly.Location` is a member) ...
            for i in range(len(parts), 1, -1):           # ... unless a prefix of it is a qualified type name (`Backend.Models.Product.Location`)
                if ".".join(parts[:i]) in full_names:
                    counts[".".join(parts[:i])] += 1
                    break
            else:
                counts[parts[0]] += 1
        for name, n in counts.items():
            if name in full_names:                       # written out with its namespace: no lookup needed
                targets, how = {full_names[name][1]}, "qualified"
            else:
                decl = declared.get(name)
                if not decl or any(g == f for _, g in decl):
                    continue                             # not a type, or the file declares the name itself (its own type, a part of a partial type)
                seen = {(ns, g) for ns, g in decl if ns in visible}
                if not seen:
                    report["not in scope"] += 1          # a property, enum member or variable with the name of a type the file cannot see
                    continue
                targets = {g for _, g in seen}
                how = "unique" if len(decl) == 1 else "partial" if len({ns for ns, _ in decl}) == 1 else \
                      "by namespace" if len({ns for ns, _ in seen}) == 1 else "ambiguous"
            if f in targets:
                continue
            report[how] += 1
            for g in targets:
                edges[(f, g)] += n
                resolution[(f, g)] = how if resolution.get((f, g)) in (None, how) else "mixed"

    out.mkdir(parents=True, exist_ok=True)
    with open(out / "code-edges.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["source", "target", "kind", "weight", "resolution"])
        for (s, g), n in sorted(edges.items()):
            w.writerow([s, g, "code", n, resolution[(s, g)]])
    multi = sorted((name, len(d)) for name, d in declared.items() if len({ns for ns, _ in d}) > 1)
    print(f"{len(texts)} .cs files, {sum(len(d) for d in declared.values())} type declarations, {len(edges)} code edges "
          f"({', '.join(f'{k} {v}' for k, v in report.most_common())}); {len(multi)} type names declared in several namespaces"
          f"{': ' + ', '.join(n for n, _ in multi[:10]) if multi else ''} -> {out / 'code-edges.csv'}", file=sys.stderr)


if __name__ == "__main__":
    main()
