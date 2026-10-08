#!/usr/bin/env python3
"""Change coupling after Adam Tornhill: files that change in the same commits, and in the same tickets, compared with what is already known.

For every pair of files with enough shared changesets it computes the degree of coupling = shared / ((revisions_a + revisions_b) / 2), once per
commit and once per ticket (the union of the files of all commits that carry the ticket number), and then asks the question this skill exists for:
is there any dependency between the two that we already know? A pair with none is a **candidate for a hidden dependency**: two files that
must change together and are not connected by the code graph, by wiring, by a URL, by a name or by a shared table.

Known means: a path from one file to the other in the code graph plus the "use" edges (a call-like link, followed transitively), a direct edge of
the weaker kinds (URL, shared name), or a table both use. The code graph is a file of edges (source,target,kind; any tool may write it, see SKILL.md).

  python3 -I <skill dir>/scripts/change_coupling.py [--repo <path>] [--out <folder>] [--config <overrides.yaml>]
                                                    [--code-edges <code-edges.csv>] [--edges <dependencies.csv>]
Writes change-coupling.csv and change-coupling.md. Needs PyYAML. Coupling is evidence from history, never a proof: a pair can change together
because of a shared ticket, a release, a person, or chance; the report says which of these it can tell apart and which not.
"""
import argparse, collections, csv, datetime as dt, difflib, itertools, re, subprocess, sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("Missing dependency (yaml). Run it with:\n  uv run --no-project --with pyyaml python -I " + str(Path(__file__)))

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import settings
USE = ("xml-class", "bean-ref", "orm-relation", "string-class", "bean-lookup", "prefix-class", "file-name")


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, errors="replace").stdout


def scanned_files(repo, cfg):
    return set(settings.files_in_scope(repo, cfg, git, cfg["change_coupling"].get("ignore", []))[0])


def changesets(repo, files, cc):
    """-> commit changesets {hash: set(files)}, ticket changesets {ticket: set(files)}, ticket of each commit, statistics"""
    pats = [re.compile(p, re.M) for p in cc["ticket_patterns"]]
    out = git(repo, "log", "--no-merges", "--name-only", "--format=\x1e%H\x1f%an\x1f%aI\x1f%B\x1f")
    commits, tickets, of_commit, meta = {}, collections.defaultdict(set), {}, {}
    stat = collections.Counter()
    for chunk in out.split("\x1e")[1:]:
        h, author, date, msg, names = chunk.split("\x1f", 4)
        fs = {n for n in names.split("\n") if n in files}
        stat["commits"] += 1
        if not fs:
            continue
        if len(fs) > cc["max_files_per_commit"]:
            stat["commits_too_large"] += 1
            continue
        commits[h] = fs
        meta[h] = (author, date[:10])
        ids = {m.group(1).upper() for p in pats for m in p.finditer(msg)}
        if ids:
            stat["commits_with_ticket"] += 1
            of_commit[h] = ids
            for t in ids:
                tickets[t] |= fs
    big = [t for t, fs in tickets.items() if len(fs) > cc["max_files_per_ticket"]]
    for t in big:
        del tickets[t]
    stat["tickets"], stat["tickets_too_broad"] = len(tickets) + len(big), len(big)
    return commits, tickets, of_commit, stat, meta


def coupling(sets, cc):
    """-> {(a, b): (shared, degree in percent)} over the changesets, by code-maat's definition."""
    revs, pairs = collections.Counter(), collections.Counter()
    for fs in sets.values():
        fs = sorted(fs)
        revs.update(fs)
        pairs.update(itertools.combinations(fs, 2))
    out = {}
    for (a, b), n in pairs.items():
        if n < cc["min_shared"] or revs[a] < cc["min_revisions"] or revs[b] < cc["min_revisions"]:
            continue
        deg = 100 * n / ((revs[a] + revs[b]) / 2)
        if deg >= cc["min_degree"]:
            out[(a, b)] = (n, deg)
    return out


def load_graph(code_edges, dep_edges, kinds):
    """Known relations: `hard` = code graph and use edges (followed transitively), `soft` = weaker kinds (direct only), `tables` = table of a file."""
    hard, soft, tables = collections.defaultdict(set), collections.defaultdict(set), collections.defaultdict(set)
    if code_edges:
        with open(code_edges, newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                hard[r["source"]].add(r["target"])
    if dep_edges:
        with open(dep_edges, newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                k = r["kind"]
                if k in USE and "use" in kinds:
                    hard[r["source"]].add(r["target"])
                elif k in ("url-link", "key-link") and "links" in kinds:
                    soft[r["source"]].add(r["target"])
                elif k == "name-link" and "names" in kinds:
                    soft[r["source"]].add(r["target"])
                elif k == "data-table":
                    tables[r["source"]].add(r["target"])
                elif k == "table-defined-in":                       # source is the table node, target the changelog or script that creates or alters it
                    tables[r["target"]].add(r["source"])
    return hard, soft, tables


def within(hard, start, steps, cache):
    """{file: distance} for everything reachable from `start` in at most `steps` steps along `hard` edges."""
    key = (start, steps)
    if key not in cache:
        seen, frontier = {start: 0}, [start]
        for d in range(1, steps + 1):
            nxt = []
            for x in frontier:
                for y in hard.get(x, ()):
                    if y not in seen:
                        seen[y] = d
                        nxt.append(y)
            frontier = nxt
        cache[key] = seen
    return cache[key]


def known_by(a, b, hard, soft, tables, cache, steps):
    d = min(within(hard, a, steps, cache).get(b, 99), within(hard, b, steps, cache).get(a, 99))
    if d <= steps:
        return f"code graph or use edge ({d} step{'s' if d > 1 else ''})"
    if b in soft.get(a, ()) or a in soft.get(b, ()):
        return "URL, key or shared name"
    if tables.get(a, set()) & tables.get(b, set()):
        return "shared table"
    near = lambda f: set().union(*(tables.get(x, set()) for x in within(hard, f, steps, cache)))     # tables of the file and of what it reaches in a few steps
    if near(a) & near(b):
        return f"shared table through code (within {steps} steps)"
    if hard.get(a, set()) & hard.get(b, set()):
        return "siblings: both depend on the same file"
    return ""


def module_of(f):
    return f.split("/", 1)[0] if "/" in f else "."


def kind_of(f):
    return f.rsplit(".", 1)[-1] if "." in f else "?"


# ---------------------------------------------------------------- patterns behind a pair

WORD = re.compile(r"[A-Za-z_][A-Za-z0-9_]{5,}")
PARTS = re.compile(r"[A-Z]?[a-z0-9]+|[A-Z]+(?![a-z])")


def interesting(w, pc):
    """A word that looks like an identifier rather than ordinary text: mixed case, an underscore, a digit, or long."""
    return len(w) >= pc["rare_min_length"] and (re.search(r"[a-z][A-Z]|_|\d", w) or len(w) >= 10)


def vocabulary(repo, files, pc):
    """-> (document frequency of every interesting word over all files, the set of words per file)"""
    per_file, df = {}, collections.Counter()
    for f in files:
        try:
            t = (repo / f).read_text(errors="replace")
        except OSError:
            continue
        ws = {w for w in WORD.findall(t) if interesting(w, pc)}
        per_file[f] = ws
        df.update(ws)
    return df, per_file


def name_parts(f):
    return {p.lower() for p in PARTS.findall(Path(f).stem.replace("-", "_")) if len(p) > 1 and not p.isdigit()}


def layer_of(f, layers):
    for name, rx in layers:
        if rx.search(f):
            return name
    return "other"


def line_similarity(repo, a, b, limit):
    try:
        la = [l.strip() for l in (repo / a).read_text(errors="replace").splitlines() if l.strip()]
        lb = [l.strip() for l in (repo / b).read_text(errors="replace").splitlines() if l.strip()]
    except OSError:
        return None
    if not la or not lb or max(len(la), len(lb)) > limit:
        return None
    return difflib.SequenceMatcher(None, la, lb, autojunk=False).ratio()


def pair_patterns(repo, a, b, commit_ids, commits, meta, df, per_file, layers, pc):
    """Hypotheses about why two files change together, each with its evidence. -> (labels, evidence dict)"""
    labels, ev = [], {}
    sim = line_similarity(repo, a, b, pc["max_lines_for_similarity"])
    ev["similarity"] = None if sim is None else round(sim, 2)
    if sim is not None and sim >= pc["clone_similarity"]:
        labels.append("clone")
    shared = sorted((w for w in per_file.get(a, set()) & per_file.get(b, set()) if df[w] <= pc["rare_max_files"]), key=lambda w: (df[w], w))
    ev["shared_words"] = shared[:5]
    ev["shared_word_count"] = len(shared)
    if len(shared) >= pc["min_shared_rare"]:
        labels.append("shared vocabulary")
    same_dir = Path(a).parent == Path(b).parent
    common = name_parts(a) & name_parts(b)
    ev["name_parts"] = sorted(common)
    if same_dir and len(common) >= pc["min_shared_name_parts"]:
        labels.append("naming family")
    la, lb = layer_of(a, layers), layer_of(b, layers)
    ev["layers"] = la if la == lb else f"{la} + {lb}"
    if la != lb and ("shared vocabulary" in labels or common):
        labels.append("vertical slice")
    ds = sorted(meta[h][1] for h in commit_ids)
    if ds:
        d0, d1 = dt.date.fromisoformat(ds[0]), dt.date.fromisoformat(ds[-1])
        span = (d1 - d0).days
        ev["first"], ev["last"], ev["span_days"] = ds[0], ds[-1], span
        days = [dt.date.fromisoformat(x) for x in ds]
        best = max(sum(1 for y in days if 0 <= (y - x).days <= pc["burst_days"]) for x in days)
        burst = best / len(days) >= pc["burst_share"]
        if burst:
            labels.append("burst")
        elif span >= pc["persistent_days"]:
            labels.append("persistent")
        who = collections.Counter(meta[h][0] for h in commit_ids)
        top, n = who.most_common(1)[0]
        ev["top_author_share"] = round(n / len(commit_ids), 2)
        if len(commit_ids) >= 5 and n / len(commit_ids) >= pc["one_person_share"]:
            labels.append("one person")
        sizes = sorted(len(commits[h]) for h in commit_ids)
        ev["median_files"] = sizes[len(sizes) // 2]
        if ev["median_files"] >= pc["bulk_files"]:
            labels.append("bulk change")
    return labels, ev


PATTERN_MEANING = {
    "clone": "the files are copies of each other that evolved in parallel: a duplicated structure that wants one shared abstraction",
    "shared vocabulary": "rare words occur in both: a shared concept, a column, a key or a contract that is spelled out twice",
    "naming family": "a family of parallel files in one folder (variants of one thing): changes to the family go to every member",
    "vertical slice": "the files sit in different layers and share a concept: one feature runs through them, a change to it touches each layer",
    "burst": "the shared changes fall into a short period: one event (a feature, a refactoring, a release), not a standing link",
    "persistent": "the shared changes recur over a year or more: a standing link that survives events",
    "one person": "one author made nearly all the shared changes: the coupling may be that person's habit, and the knowledge sits with them",
    "bulk change": "the shared commits are large: mostly mechanical changes (renames, formatting) that say little about a dependency",
}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", default=".")
    ap.add_argument("--out", default=None, help="default <repo>/temp/dependency-map")
    ap.add_argument("--config", default=None, help="overrides for this repository, merged over the defaults (dependency-map.yaml of the skill)")
    ap.add_argument("--code-edges", default=None, help="edge list of the code graph (source,target,...), source,target,kind; written by any code-graph tool, see SKILL.md")
    ap.add_argument("--edges", default=None, help="dependencies.csv of this skill (default: <out>/dependencies.csv if present)")
    a = ap.parse_args()
    repo = Path(a.repo).resolve()
    out = Path(a.out).resolve() if a.out else repo / "temp" / "dependency-map"
    cfg = settings.load(a.config)
    cc = cfg["change_coupling"]
    out.mkdir(parents=True, exist_ok=True)
    dep = Path(a.edges) if a.edges else out / "dependencies.csv"
    dep = dep if dep.exists() else None

    files = scanned_files(repo, cfg)
    commits, tickets, of_commit, stat, meta = changesets(repo, files, cc)
    by_commit, by_ticket = coupling(commits, cc), coupling(tickets, cc)
    hard, soft, tables = load_graph(a.code_edges, dep, cc["known_edge_kinds"])
    have_graph = bool(hard)
    ticket_of_file = collections.defaultdict(set)
    for t, fs in tickets.items():
        for f in fs:
            ticket_of_file[f].add(t)
    rows, cache = [], {}
    for pair in sorted(set(by_commit) | set(by_ticket)):
        a_, b_ = pair
        sc, dc = by_commit.get(pair, (0, 0.0))
        st, dt_ = by_ticket.get(pair, (0, 0.0))
        shared_tickets = sorted(ticket_of_file[a_] & ticket_of_file[b_])
        known = known_by(a_, b_, hard, soft, tables, cache, cc["known_max_steps"]) if have_graph else "unknown (no code edges given)"
        rows.append({"file_a": a_, "file_b": b_, "level": "both" if pair in by_commit and pair in by_ticket else "commit" if pair in by_commit else "ticket",
                     "shared_commits": sc, "degree_commits": round(dc), "shared_tickets": st, "degree_tickets": round(dt_), "known_by": known,
                     "hidden": "" if not have_graph else "yes" if not known else "sibling" if known.startswith("siblings") else "no",
                     "types": "/".join(sorted({kind_of(a_), kind_of(b_)})), "cross_module": "yes" if module_of(a_) != module_of(b_) else "no",
                     "tickets": " ".join(shared_tickets[:4])})
    pc = cfg["patterns"]
    layers = [(l["name"], re.compile(l["pattern"])) for l in pc["layers"]]
    df, per_file = vocabulary(repo, sorted(files), pc)
    cof = collections.defaultdict(set)
    for h, fs in commits.items():
        for f in fs:
            cof[f].add(h)
    evid = {}
    for r in rows:
        labels, ev = pair_patterns(repo, r["file_a"], r["file_b"], cof[r["file_a"]] & cof[r["file_b"]], commits, meta, df, per_file, layers, pc)
        evid[(r["file_a"], r["file_b"])] = (labels, ev)
        r.update({"patterns": ", ".join(labels) or "none found", "similarity": "" if ev["similarity"] is None else ev["similarity"],
                  "shared_words": " ".join(ev["shared_words"]), "layers": ev["layers"], "span_days": ev.get("span_days", ""),
                  "top_author_share": ev.get("top_author_share", "")})
    with (out / "change-coupling.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]) if rows else ["file_a"])
        w.writeheader()
        for r in sorted(rows, key=lambda r: (r["hidden"] != "yes", -max(r["degree_commits"], r["degree_tickets"]), -(r["shared_commits"] + r["shared_tickets"]))):
            w.writerow(r)

    n = len(rows)
    hid = [r for r in rows if r["hidden"] == "yes"]
    L = ["# Change coupling and hidden dependencies\n",
         f"Generated {dt.datetime.now().replace(microsecond=0).isoformat()} · commit `{git(repo, 'rev-parse', '--short', 'HEAD').strip()}` · {len(files)} files in scope\n",
         "> Tornhill's change coupling: files that change in the same commits or the same tickets. **Degree** = shared / ((revisions of a + revisions of b) / 2). "
         "A pair is **hidden** when no known dependency connects the two files: not the code graph or wiring within " + str(cc["known_max_steps"]) + " steps, not a URL or a shared name, "
         "not a shared table, and the two do not even depend on a common file. Coupling is evidence from history, never a proof: the same ticket, release, person or chance can explain it.\n",
         "## What the history offers\n",
         f"- Commits: {stat['commits']}; used {len(commits)} (larger than {cc['max_files_per_commit']} files left out: {stat['commits_too_large']}).",
         f"- Tickets: {stat['tickets']} found in {stat['commits_with_ticket']} commits ({100 * stat['commits_with_ticket'] / max(len(commits), 1):.0f}% of the commits used); "
         f"{stat['tickets_too_broad']} touched more than {cc['max_files_per_ticket']} files and are left out. Commits without a ticket number take part in the commit level only.",
         f"- Thresholds: at least {cc['min_revisions']} revisions per file, {cc['min_shared']} shared changesets, degree {cc['min_degree']} % (all `[own]`, see `dependency-map.yaml`).",
         f"- Coupled pairs: {len(by_commit)} by commit, {len(by_ticket)} by ticket, {n} in all ({sum(1 for r in rows if r['level'] == 'both')} on both levels).\n"]
    if not have_graph:
        L.append("**No code edges given:** which pairs are already known cannot be told. Pass `--code-edges` (the code-graph edge list described in SKILL.md).\n")
    else:
        k = collections.Counter(r["known_by"] or "none: hidden" for r in rows)
        L += ["## Known and hidden\n", "| Pair is connected by | Pairs | Share |", "|---|---:|---:|"]
        L += [f"| {name} | {c} | {100 * c / n:.0f} % |" for name, c in k.most_common()]
        strong = sum(c for name, c in k.items() if name.startswith("code graph or use edge (1") or name in ("shared table", "URL, key or shared name"))
        none = k.get("none: hidden", 0)
        L += ["", f"**By strength of the explanation:** direct {strong} ({100 * strong / n:.0f} %: a code or use edge in one step, a URL, key or name, a table both use), "
              f"indirect {n - strong - none} ({100 * (n - strong - none) / n:.0f} %: two steps, a table reached through code, or only a shared dependency, weaker "
              f"because a hub such as the table `study` links almost anything), none {none} ({100 * none / n:.0f} %)."]
        L += ["", f"**{len(hid)} of {n} coupled pairs have no known dependency and share no dependency either** (`siblings` are pairs without a path between them that depend on a common file: the same structure, often a copy that evolved in parallel). By file types of the pair, and across modules:\n", "| Types | Hidden pairs | Across modules |", "|---|---:|---:|"]
        by_type = collections.Counter(r["types"] for r in hid)
        for t, c in by_type.most_common(8):
            L.append(f"| {t} | {c} | {sum(1 for r in hid if r['types'] == t and r['cross_module'] == 'yes')} |")
        both = [r for r in hid if r["level"] == "both"]
        L += ["", f"## Hidden pairs that are coupled on both levels, commit and ticket ({len(both)}): the strongest leads\n",
              "| File A | File B | Commits (degree) | Tickets (degree) | Example tickets |", "|---|---|---|---|---|"]
        for r in sorted(both, key=lambda r: -(r["degree_commits"] + r["degree_tickets"]))[:25]:
            L.append(f"| `{r['file_a']}` | `{r['file_b']}` | {r['shared_commits']} ({r['degree_commits']} %) | {r['shared_tickets']} ({r['degree_tickets']} %) | {r['tickets']} |")
        only_t = [r for r in hid if r["level"] == "ticket"]
        L += ["", f"## Hidden pairs found only through tickets ({len(only_t)}): the same work item, different commits\n",
              "| File A | File B | Tickets (degree) | Example tickets |", "|---|---|---|---|"]
        for r in sorted(only_t, key=lambda r: -r["degree_tickets"])[:15]:
            L.append(f"| `{r['file_a']}` | `{r['file_b']}` | {r['shared_tickets']} ({r['degree_tickets']} %) | {r['tickets']} |")
    L += ["", "## Why might they change together? Patterns behind the pairs\n",
          "> Hypotheses, not findings: each label is a possible reason with its evidence. A pair can carry several, or none. Coupling says that files change together, "
          "never why; the labels narrow down where to look and what the fix would be.\n",
          "| Pattern | Hidden pairs | All pairs | What it suggests | Strongest example |", "|---|---:|---:|---|---|"]
    hid_keys = {(r["file_a"], r["file_b"]) for r in rows if r["hidden"] == "yes"}
    for lab, meaning in PATTERN_MEANING.items():
        ks = [k for k, (ls, _) in evid.items() if lab in ls]
        hk = [k for k in ks if k in hid_keys]
        pool = hk or ks
        ex = max(pool, key=lambda k: (by_commit.get(k, (0, 0))[1] + by_ticket.get(k, (0, 0))[1])) if pool else None
        L.append(f"| {lab} | {len(hk)} | {len(ks)} | {meaning} | " + (f"`{Path(ex[0]).name}` + `{Path(ex[1]).name}`" if ex else "–") + " |")
    nopat = [k for k in hid_keys if not evid[k][0]]
    if have_graph:
        L += ["", f"{len(nopat)} of the {len(hid_keys)} hidden pairs carry no pattern at all: the reason they change together stays open, and they are the first to ask a person about.", ""]
        L += ["### The hidden pairs and their evidence\n", "| File A | File B | Patterns | Evidence |", "|---|---|---|---|"]
        for k in sorted(hid_keys, key=lambda k: -(by_commit.get(k, (0, 0))[1] + by_ticket.get(k, (0, 0))[1]))[:25]:
            labels, ev = evid[k]
            bits = []
            if ev["similarity"] is not None:
                bits.append(f"{ev['similarity']:.0%} similar lines")
            if ev["shared_words"]:
                bits.append(f"{ev['shared_word_count']} rare shared words, e.g. {', '.join('`' + w + '`' for w in ev['shared_words'][:3])}")
            if ev.get("span_days") is not None:
                bits.append(f"{ev['first']} to {ev['last']}")
            if ev.get("top_author_share") is not None:
                bits.append(f"top author {ev['top_author_share']:.0%}")
            bits.append(ev["layers"])
            L.append(f"| `{k[0]}` | `{k[1]}` | {', '.join(labels) or 'none found'} | {'; '.join(bits)} |")
    L += ["", "## What this cannot tell\n",
          "- Why the files change together. A release ticket, a person who always touches both, or a rename can look like a dependency.",
          "- Tickets are only as good as the commit messages: commits without a number take part in the commit level only.",
          "- Pairs below the thresholds, and files with few revisions, are not judged. A rarely changed file can hide a dependency that never showed.",
          "- Known means connected in the graphs we have; an edge that none of the skills can see (a call to another system) is missing from both sides."]
    (out / "change-coupling.md").write_text("\n".join(L) + "\n")
    print(f"{n} coupled pairs ({len(by_commit)} commit, {len(by_ticket)} ticket)" + (f", {len(hid)} without a known dependency" if have_graph else "") + f" -> {out}")


if __name__ == "__main__":
    main()
