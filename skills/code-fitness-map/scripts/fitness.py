#!/usr/bin/env python3
"""Code fitness per file, fit, strained or unfit.

Measures smells with lizard (functions, cyclomatic complexity, code lines, arguments; many languages),
an own scanner for the nesting depth, and Git; weighs them with weights.yaml and writes fitness.csv (one row per file),
fitness.md (summary per unit) and bubbles.html. Deterministic, no LLM. The levels are our own heuristic.

  python3 -I <skill dir>/scripts/fitness.py [--repo <path>] [--out <folder>] [--config <weights.yaml>]
                                                              [--active-authors <file>]
needs lizard and PyYAML, for example:
  uv run --no-project --with lizard --with pyyaml python -I <skill dir>/scripts/fitness.py
"""
import argparse, collections, csv, datetime as dt, difflib, json, os, re, subprocess, sys
from pathlib import Path

try:
    import lizard
    import yaml
except ImportError as e:
    sys.exit(f"Missing dependency ({e.name}). Run it with:\n  uv run --no-project --with lizard --with pyyaml python -I {Path(__file__)}")

HERE = Path(__file__).resolve().parent
LEVELS = ("unfit", "strained", "fit")
EXT = {"java": (".java",), "javascript": (".js", ".mjs", ".jsx"), "typescript": (".ts", ".tsx"), "python": (".py",), "csharp": (".cs",),
       "c": (".c", ".h"), "cpp": (".cpp", ".cc", ".cxx", ".hpp"), "go": (".go",), "rust": (".rs",), "kotlin": (".kt",), "scala": (".scala",),
       "swift": (".swift",), "php": (".php",), "ruby": (".rb",)}
NO_BRACES = {"python", "ruby"}      # the nesting scanner counts braces; for these languages the depth is not measured
LANG_OF = {e: lang for lang, exts in EXT.items() for e in exts}


def log(msg):
    print(msg, file=sys.stderr)


# ---------------------------------------------------------------- scope

def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, errors="replace").stdout


def list_files(repo, cfg):
    langs = cfg["scope"]["languages"]
    langs = list(EXT) if langs in ("auto", ["auto"]) else langs
    exts = tuple(e for lang in langs for e in EXT[lang])
    exclude = [re.compile(p) for p in cfg["scope"].get("exclude", [])]
    tracked = git(repo, "ls-files", "-z").split("\0")
    names = [n for n in tracked if n] or [p.relative_to(repo).as_posix() for p in repo.rglob("*") if p.is_file()]
    return sorted(n for n in names if n.endswith(exts) and not any(e.search(n) for e in exclude) and (repo / n).is_file())


# ---------------------------------------------------------------- nesting depth

TOK = re.compile(r'//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\\n])*"|\'(?:\\.|[^\'\\\n])*\'|`[^`]*`|[A-Za-z_$][\w$]*|[{}();]', re.S)
CONDS = ("if", "for", "while", "switch", "do", "catch")


def nesting_depth(body):
    """Deepest nesting of conditionals and loops in a function body (text starting at its first '{').

    A tolerant scanner, not a parser. An `else` block counts as a level of its own. Braceless bodies are tracked until their `;`."""
    toks = [m.group(0) for m in TOK.finditer(body) if not m.group(0).startswith(("//", "/*", '"', "'", "`"))]
    stack, i, n, maxd, last_closed = [], 0, len(toks), 0, None
    depth = lambda: sum(1 for f in stack if f != "b")
    while i < n:
        t = toks[i]
        if t == "else" and i + 1 < n and toks[i + 1] == "{":
            stack.append("c"); maxd = max(maxd, depth()); i += 2; last_closed = None
            continue
        if t in CONDS and not (t == "while" and last_closed == "do"):
            j = i + 1
            if t != "do" and j < n and toks[j] == "(":
                d = 0
                while j < n:
                    d += toks[j] == "("; d -= toks[j] == ")"; j += 1
                    if d == 0:
                        break
            if j < n and toks[j] == "{":
                stack.append("cd" if t == "do" else "c"); maxd = max(maxd, depth()); i = j + 1; last_closed = None
                continue
            stack.append("n"); maxd = max(maxd, depth()); i = j
            continue
        if t == "{":
            stack.append("b")
        elif t == "}":
            if stack:
                last_closed = "do" if stack.pop() == "cd" else None
        elif t == ";":
            while stack and stack[-1] == "n":
                stack.pop()
        i += 1
    return maxd


# ---------------------------------------------------------------- code duplication

STRUCT = set("if else for while do switch case break continue return try catch finally throw new this null true false function var let const default".split())
NORM = re.compile(r'//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\\n])*"|\'(?:\\.|[^\'\\\n])*\'|`[^`]*`|[A-Za-z_$][\w$]*|\d[\w.]*|\S', re.S)


def normalise(text):
    """Token sequence of a function with identifiers and literals blanked: what is left is its structure."""
    out = []
    for m in NORM.finditer(text):
        t = m.group(0)
        if t.startswith(("//", "/*")):
            continue
        out.append("L" if t[0] in "\"'`" or t[0].isdigit() else (t if t in STRUCT else "I") if t[0].isalpha() or t[0] in "_$" else t)
    return out


def similar_functions(funcs, texts, min_lines, min_sim):
    """Indices of functions (at least min_lines code lines) that have a structurally similar sibling in the same file."""
    idx = [i for i, f in enumerate(funcs) if f["nloc"] >= min_lines]
    toks = {i: normalise(texts[i]) for i in idx}
    cnt = {i: collections.Counter(t) for i, t in toks.items()}
    hit = set()
    for a in range(len(idx)):
        for b in range(a + 1, len(idx)):
            i, j = idx[a], idx[b]
            la, lb = len(toks[i]), len(toks[j])
            if not la or not lb or min(la, lb) / max(la, lb) < 2 * min_sim - 1:          # ratio <= 2*min/(la+lb)
                continue
            if 2 * sum((cnt[i] & cnt[j]).values()) / (la + lb) < min_sim:               # cheap bound before the exact ratio
                continue
            if difflib.SequenceMatcher(None, toks[i], toks[j], autojunk=False).ratio() >= min_sim:
                hit.update((i, j))
    return sorted(hit)


# ---------------------------------------------------------------- measuring

ASSIGNED = re.compile(r"""([\w$.'"]+)\s*[:=]\s*function\b""")


def assigned_name(name, first_line):
    """lizard calls `a.b = function () {` or `key: function () {` anonymous; the name is on the line where it starts."""
    if name != "(anonymous)":
        return name
    m = ASSIGNED.search(first_line)
    return m.group(1).strip("'\"") if m else name


def measure(repo, rel, cfg):
    """-> {'nloc': code lines of the file, 'funcs': [{name, begin, end, nloc, cc, args, depth}], 'dups': [names]}"""
    a = lizard.analyze_file(str(repo / rel))
    lines = (repo / rel).read_text(errors="replace").splitlines()
    funcs, texts = [], []
    for f in a.function_list:
        body = "\n".join(lines[f.start_line - 1:f.end_line])
        k = body.find("{")
        texts.append(body)
        funcs.append({"name": assigned_name(f.name, lines[f.start_line - 1]), "begin": f.start_line, "end": f.end_line, "nloc": f.nloc, "cc": f.cyclomatic_complexity,
                      "args": f.parameter_count, "depth": None if LANG_OF.get(Path(rel).suffix) in NO_BRACES else nesting_depth(body[k:]) if k >= 0 else 0})
    dd = cfg["detect"]["duplication"]
    dups = [funcs[i]["name"] for i in similar_functions(funcs, texts, dd["min_lines"], dd["similarity"])]
    return {"nloc": a.nloc, "funcs": funcs, "dups": dups}


# ---------------------------------------------------------------- Git

def load_active(path):
    if not path or not Path(path).exists():
        return None
    return {l.strip().lower() for l in Path(path).read_text().splitlines() if l.strip() and not l.startswith("#")}


def history(repo, cfg, files):
    """-> {file: {'days', 'authors', 'lookback'}}, commits used, mass commits skipped, anchor date"""
    h, d = cfg["history"], cfg["detect"]["former_contributors"]
    months = max(h["window_months"], d["lookback_months"])
    anchor = git(repo, "log", "-1", "--no-merges", "--format=%as", "--", *files).strip() or dt.date.today().isoformat()
    end = dt.date.fromisoformat(anchor)
    win_from = (end - dt.timedelta(days=30 * h["window_months"])).isoformat()
    since = (end - dt.timedelta(days=30 * months)).isoformat()
    out = git(repo, "log", f"--since={since}", "--no-merges", "--name-only", "--format=\x1e%as\x1f%aN\x1f%aE")
    want, res, used, skipped = set(files), collections.defaultdict(lambda: {"days": set(), "authors": set(), "lookback": set()}), 0, 0
    for chunk in out.split("\x1e")[1:]:
        head, *names = chunk.strip("\n").split("\n")
        date, name, mail = head.split("\x1f")
        names = [n for n in names if n]
        if len(names) > h["ignore_commits_over_files"]:
            skipped += 1
            continue
        used += 1
        for n in names:
            if n in want:
                r = res[n]
                r["lookback"].add((name.lower(), mail.lower()))
                if date >= win_from:
                    r["days"].add(date)
                    r["authors"].add(name.lower())
    return res, used, skipped, anchor


# ---------------------------------------------------------------- classification

def classify(m, hist, active, cfg):
    d, w = cfg["detect"], cfg["smells"]
    cx, cx_alert = d["complex_method"]["cyclomatic"], d["complex_method"]["alert_cyclomatic"]
    ln, ln_alert = d["large_method"]["lines"], d["large_method"]["alert_lines"]
    depth_max, args_max = d["nested_complexity"]["depth"], d["excess_arguments"]["max"]
    kinds = collections.defaultdict(lambda: {"warn": 0, "alert": 0, "notes": []})

    def hit(kind, note, alert=False):
        k = kinds[kind]
        k["alert" if alert else "warn"] += 1
        k["notes"].append(note)

    worst = (None, 0)
    for f in m["funcs"]:
        label = f"{f['name']}() cc {f['cc']}, {f['nloc']} lines, depth {'n/a' if f['depth'] is None else f['depth']}, {f['args']} args"
        if f["cc"] > worst[1]:
            worst = (f["name"], f["cc"])
        if f["cc"] >= cx and f["nloc"] >= ln and (f["depth"] is None or f["depth"] >= depth_max) and f["args"] > args_max:
            hit("brain_method", f"Brain Method: {label}")
            continue                                            # a Brain Method is not also counted as complex or large
        if f["cc"] >= cx:
            hit("complex_method", f"Complex Method: {label}", alert=f["cc"] >= cx_alert)
        if f["nloc"] >= ln and f["name"] != "(anonymous)":
            hit("large_method", f"Large Method: {label}", alert=f["nloc"] >= ln_alert)
        if f["depth"] is not None and f["depth"] >= depth_max:
            hit("nested_complexity", f"Nested Complexity: {f['name']}() depth {f['depth']}")
        if f["args"] > args_max:
            hit("excess_arguments", f"Excess arguments: {f['name']}() {f['args']}")
    bc = d["brain_class"]
    if kinds["brain_method"]["warn"] and m["nloc"] >= bc["min_lines"] and len(m["funcs"]) >= bc["min_functions"]:
        hit("brain_class", f"Brain Class ({len(m['funcs'])} functions, {m['nloc']} lines, a Brain Method)")
    lf = d["large_file"]
    if m["nloc"] >= lf["lines"]:
        hit("large_file", f"Large file: {m['nloc']} lines", alert=m["nloc"] >= lf["alert_lines"])
    if m["funcs"]:
        mean = sum(f["cc"] for f in m["funcs"]) / len(m["funcs"])
        if mean >= d["overall_complexity"]["mean_cyclomatic"]:
            hit("overall_complexity", f"Overall complexity: mean cc {mean:.1f}")
    if m["dups"]:
        hit("duplication", f"Code duplication: {len(m['dups'])} functions with similar structure ({', '.join(m['dups'][:4])}{', ...' if len(m['dups']) > 4 else ''})")
    h = hist or {"days": set(), "authors": set(), "lookback": set()}
    if len(h["authors"]) >= d["developer_congestion"]["authors"]:
        hit("developer_congestion", f"Developer Congestion: {len(h['authors'])} authors in the window")
    former = None
    if active is not None:
        former = bool(h["lookback"]) and not any(n in active or e in active for n, e in h["lookback"])
        if former and any(k for k in kinds if k != "developer_congestion"):
            hit("former_contributors", "Complex code by former contributors")
    score = 0
    for kind, k in kinds.items():
        c = w[kind]
        score += min(k["warn"] * c["weight"] + k["alert"] * c.get("alert_weight", c["weight"]), c["cap"])
    lv = cfg["levels"]
    level = "unfit" if score >= lv["unfit"] else "strained" if score >= lv["strained"] else "fit"
    count = lambda kind: kinds[kind]["warn"] + kinds[kind]["alert"] if kind in kinds else 0
    return {"level": level, "score": score, "notes": [n for kind in kinds for n in kinds[kind]["notes"][:5]], "worst": worst, "former": former,
            "alert_complex": kinds["complex_method"]["alert"] if "complex_method" in kinds else 0,
            "alert_large": kinds["large_method"]["alert"] if "large_method" in kinds else 0,
            **{k: count(k) for k in ("brain_class", "brain_method", "complex_method", "large_method", "nested_complexity",
                                     "excess_arguments", "large_file", "overall_complexity", "duplication", "developer_congestion")}}


# ---------------------------------------------------------------- units

def source_root(path, patterns):
    """-> (root, rest) for the first pattern of scope.source_roots that matches, e.g. 'x/src/main/java/' and 'org/foo/A.java'."""
    for p in patterns:
        mt = re.match(rf"^(.*?(?:{p}))(.*)$", path)
        if mt:
            return mt.group(1), mt.group(2)
    return None


def package_prefixes(files, patterns):
    roots = collections.defaultdict(list)
    for f in files:
        mt = source_root(f, patterns)
        if mt:
            roots[mt[0]].append(mt[1].split("/")[:-1])
    out = {}
    for root, dirs in roots.items():
        common = os.path.commonprefix(dirs) if dirs else []
        out[root] = "/".join(common) + "/" if common else ""
    return out


def unit_of(path, prefixes, depth):
    """Folder below the common prefix of the source root (package prefix), `depth` levels deep. Files outside a source root: their folder."""
    for root, common in prefixes.items():
        if path.startswith(root):
            rest = path[len(root):]
            if common and rest.startswith(common):
                rest = rest[len(common):]
            parts = rest.split("/")[:-1][:depth]
            return root + common + "/".join(parts) if parts else (root + common).rstrip("/") or "."
    return path.rsplit("/", 1)[0] if "/" in path else "."


# ---------------------------------------------------------------- output

def write_csv(path, rows):
    cols = ["path", "loc", "level", "score", "brain_class", "brain_method", "complex_method", "alert_complex", "large_method", "alert_large",
            "nested_complexity", "excess_arguments", "large_file", "overall_complexity", "duplication", "developer_congestion", "former_contributors",
            "functions", "change_days", "authors", "worst_function", "worst_cc"]
    with path.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(cols)
        for r in rows:
            w.writerow([r["path"], r["loc"], r["level"], r["score"], r["brain_class"], r["brain_method"], r["complex_method"], r["alert_complex"],
                        r["large_method"], r["alert_large"], r["nested_complexity"], r["excess_arguments"], r["large_file"],
                        r["overall_complexity"], r["duplication"], r["developer_congestion"], "" if r["former"] is None else int(r["former"]),
                        r["functions"], r["change_days"], r["authors"], r["worst"][0] or "", r["worst"][1] or ""])


def pct(a, b):
    return f"{100 * a / b:.0f}" if b else "–"


def write_md(path, rows, meta, cfg, units):
    tot = sum(r["loc"] for r in rows) or 1
    by = {lv: [r for r in rows if r["level"] == lv] for lv in LEVELS}
    langs = collections.Counter(r["path"].rsplit(".", 1)[-1] for r in rows)
    L = ["# Code fitness (heuristic)\n",
         f"Generated {meta['generated']} · commit `{meta['commit']}` · {len(rows)} files ({', '.join(f'{n} .{e}' for e, n in langs.items())}) · lizard {meta['lizard']} · "
         f"window {cfg['history']['window_months']} months ending at the last change to the sources ({meta['anchor']}) "
         f"({meta['commits']} commits used, {meta['skipped']} mass commits left out)\n",
         "> Levels are our own heuristic, based on smells per file in three categories, with our own thresholds, "
         "weighed with `weights.yaml`. Functions, complexity, code lines and arguments come from lizard, the nesting depth from an own scanner, "
         "authors from Git; every number has its provenance in `weights.yaml`. What could not be measured is listed at the end.\n",
         "## Overall (share of lines of code)\n",
         "| Level | Files | LOC | Share of LOC |", "|---|---:|---:|---:|"]
    for lv in LEVELS:
        L.append(f"| {lv} | {len(by[lv])} | {sum(r['loc'] for r in by[lv])} | {pct(sum(r['loc'] for r in by[lv]), tot)} % |")
    L += ["", "## Units (worst first)\n", "| Unit | Files | LOC | Unfit % LOC | Strained % LOC | Unfit files | Unfit files changed in window |", "|---|---:|---:|---:|---:|---:|---:|"]
    stats = []
    for u, rs in units.items():
        loc = sum(r["loc"] for r in rs)
        red = [r for r in rs if r["level"] == "unfit"]
        stats.append((sum(r["loc"] for r in red) / (loc or 1), u, rs, loc, red))
    for _, u, rs, loc, red in sorted(stats, key=lambda s: -s[0]):
        yl = sum(r["loc"] for r in rs if r["level"] == "strained")
        L.append(f"| `{u}` | {len(rs)} | {loc} | {pct(sum(r['loc'] for r in red), loc)} | {pct(yl, loc)} | {len(red)} | {sum(1 for r in red if r['change_days'])} |")
    hot = sorted([r for r in rows if r["level"] != "fit"], key=lambda r: (-r["change_days"], -r["score"]))[:20]
    L += ["", "## Unfit and changing (first 20)\n", "| File | Level | Score | Change days | Authors | Smells |", "|---|---|---:|---:|---:|---|"]
    for r in hot:
        L.append(f"| `{r['path']}` | {r['level']} | {r['score']} | {r['change_days']} | {r['authors']} | {'; '.join(r['notes'][:3]).replace('|', '/')} |")
    L += ["", "## Not measured\n"]
    L += [f"- **{n['smell']}**: {n['why']}" for n in cfg.get("not_measured", [])]
    nb = sum(1 for r in rows if r["path"].rsplit(".", 1)[-1] in {e.lstrip(".") for lang in NO_BRACES for e in EXT[lang]})
    if nb:
        L.append(f"- **Nested Complexity** for {nb} files in languages without braces (Python, Ruby): the nesting scanner counts braces, so depth is not measured there.")
    if meta["former"] is None:
        L.append("- **Complex code by former contributors**: no list of active people given (`detect.former_contributors.active_authors_file`).")
    path.write_text("\n".join(L) + "\n")


def write_bubbles(out, rows, meta, cfg):
    tpl = (HERE / "bubble_template.html").read_text()
    data = {"files": [[r["path"], r["loc"], r["level"], r["score"], r["notes"], r["change_days"], r["authors"]] for r in rows]}
    page = tpl.replace("__DATA__", json.dumps(data).replace("</", "<\\/")).replace("__META__", f"{meta['generated']} · commit {meta['commit']}")
    cdn = '<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.9.0/d3.min.js"></script>'
    (out / "bubbles.artifact.html").write_text(page.replace("__D3TAG__", cdn))
    d3f = out / "cache" / "d3.min.js"
    if not d3f.exists():
        try:
            import urllib.request
            d3f.parent.mkdir(exist_ok=True)
            d3f.write_bytes(urllib.request.urlopen("https://cdnjs.cloudflare.com/ajax/libs/d3/7.9.0/d3.min.js", timeout=30).read())
        except Exception as e:
            log(f"d3 could not be downloaded ({e}); bubbles.html will load it from the CDN")
    tag = "<script>" + d3f.read_text() + "</script>" if d3f.exists() else cdn
    (out / "bubbles.html").write_text("<!doctype html><html><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'></head><body>"
                                      + page.replace("__D3TAG__", tag) + "</body></html>\n")


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", default=".")
    ap.add_argument("--out", default=None, help="default <repo>/temp/code-fitness-map")
    ap.add_argument("--config", default=str(HERE.parent / "weights.yaml"))
    ap.add_argument("--active-authors", default=None, help="overrides detect.former_contributors.active_authors_file")
    a = ap.parse_args()
    repo = Path(a.repo).resolve()
    out = Path(a.out).resolve() if a.out else repo / "temp" / "code-fitness-map"
    cfg = yaml.safe_load(Path(a.config).read_text())
    out.mkdir(parents=True, exist_ok=True)
    (out / "cache").mkdir(exist_ok=True)

    files = list_files(repo, cfg)
    if not files:
        sys.exit("No source files found for the configured languages.")
    measured = {f: measure(repo, f, cfg) for f in files}
    hist, used, skipped, anchor = history(repo, cfg, files)
    af = a.active_authors or cfg["detect"]["former_contributors"].get("active_authors_file") or None
    active = load_active(af)

    rows = []
    for f in files:
        m, h = measured[f], hist.get(f)
        rows.append({"path": f, "loc": m["nloc"], "functions": len(m["funcs"]), "change_days": len(h["days"]) if h else 0,
                     "authors": len(h["authors"]) if h else 0, **classify(m, h, active, cfg)})
    prefixes = package_prefixes(files, cfg["scope"].get("source_roots", []))
    units = collections.defaultdict(list)
    for r in rows:
        units[unit_of(r["path"], prefixes, cfg["scope"]["unit_depth"])].append(r)

    meta = {"generated": dt.datetime.now().replace(microsecond=0).isoformat(), "commit": git(repo, "rev-parse", "--short", "HEAD").strip(),
            "lizard": lizard.version, "commits": used, "skipped": skipped, "anchor": anchor, "former": active}
    write_csv(out / "fitness.csv", rows)
    write_md(out / "fitness.md", rows, meta, cfg, dict(units))
    write_bubbles(out, rows, meta, cfg)
    cnt = collections.Counter(r["level"] for r in rows)
    loc_tot = sum(r["loc"] for r in rows) or 1
    print(f"{len(rows)} files: unfit {cnt['unfit']}, strained {cnt['strained']}, fit {cnt['fit']} "
          f"(unfit {pct(sum(r['loc'] for r in rows if r['level'] == 'unfit'), loc_tot)} % of LOC) -> {out}")


if __name__ == "__main__":
    main()
