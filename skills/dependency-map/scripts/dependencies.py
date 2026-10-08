#!/usr/bin/env python3
"""Dependencies between the artifacts of a codebase that a language tool does not see: XML wiring, URLs, database tables and history.

Writes dependencies.csv (one row per edge: source, target, kind, layer, confidence, evidence, weight) and dependencies.md
(what was found per kind, hubs, examples, what is not covered). Deterministic, no LLM, no network.

Layers:   structure  an edge that says "source depends on target": a change to the target can break the source
          evidence   files that changed together in Git: no direction, a hint for questions, never a reason by itself
Kinds:    xml-class     an XML file names a Java class (Spring bean, web.xml servlet/filter/listener, Hibernate mapping)
          bean-ref      a Spring bean's class depends on the class of the bean it references
          orm-relation  a mapped class depends on the class of a mapped relation
          url-link      a template, script or class names a URL that is mapped to a servlet: it depends on that servlet
          data-table    a class, mapping or template uses a table (node `table:<name>`); the table depends on the changelog or script that defines it
          file-name     a string is the name of another file of the repository (a query file, a resource, a template): the source depends on that file
          key-link      a rare key (query name, message key) is spelled the same in code and in a data file (heuristic)
          string-class  a class is named by its full name as text (reflection, JSON, properties, seed data, other XML)
          bean-lookup   code looks a Spring bean up by its id (getBean, @Qualifier, @Resource): it depends on the bean's class
          prefix-class  code builds a class name at run time from a package prefix it spells out (`"a.b.function." + name` in Class.forName): it
                        depends on every class of that package (heuristic)
          dynamic-site  code builds or looks up names at run time (node `dynamic:<call>`): its radius is a lower bound (layer evidence)
          name-link     an identifier declared in a few classes is spelled the same in another artifact (connascence of name, heuristic)
          co-change     two files changed together often (layer evidence)

  python3 -I <skill dir>/scripts/dependencies.py [--repo <path>] [--out <folder>] [--config <overrides.yaml>]
needs PyYAML, for example:  uv run --no-project --with pyyaml python -I <skill dir>/scripts/dependencies.py
"""
import argparse, collections, csv, datetime as dt, itertools, re, subprocess, sys
import xml.etree.ElementTree as ET
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("Missing dependency (yaml). Run it with:\n  uv run --no-project --with pyyaml python -I " + str(Path(__file__)))

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ecosystems as eco
import settings

KINDS = ("xml-class", "bean-ref", "orm-relation", "url-link", "data-table", "table-defined-in", "string-class", "file-name", "key-link", "bean-lookup",
         "prefix-class", "dynamic-site", "name-link", "co-change")


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, errors="replace").stdout


def local(tag):
    return tag.rsplit("}", 1)[-1]


def line_of(text, pos):
    return text.count("\n", 0, pos) + 1


class Edges:
    def __init__(self):
        self.rows = {}                                   # (source, target, kind) -> row, first evidence wins, weights add up

    def add(self, source, target, kind, layer, confidence, evidence, weight=1):
        if source == target:
            return
        key = (source, target, kind)
        if key in self.rows:
            self.rows[key]["weight"] += weight
        else:
            self.rows[key] = {"source": source, "target": target, "kind": kind, "layer": layer, "confidence": confidence,
                              "evidence": evidence, "weight": weight}


# ---------------------------------------------------------------- reading

def read_texts(repo, cfg):
    paths, active = settings.files_in_scope(repo, cfg, git)
    limit = cfg["scope"]["max_file_kb"] * 1024
    texts, skipped = {}, 0
    for f in paths:
        p = repo / f
        try:
            if p.stat().st_size > limit:
                skipped += 1
                continue
            texts[f] = p.read_text(errors="replace")
        except OSError:
            continue
    return texts, skipped, active


def is_code(f, active):
    return eco.ecosystem_of(f, active) is not None


QUOTED_DOUBLE = re.compile(r'"((?:[^"\\\n]|\\.)*)"')
QUOTED_BOTH = re.compile(r"""(?:"((?:[^"\\\n]|\\.)*)"|'((?:[^'\\\n]|\\.)*)')""")


def literals(f, t, active):
    """String literals of a code file: (content, offset of the opening quote). In C and Java a single quote is a character, not a string."""
    rx = QUOTED_DOUBLE if eco.ECOSYSTEMS[eco.ecosystem_of(f, active)].get("double_quotes_only") else QUOTED_BOTH
    for m in rx.finditer(t):
        yield (m.group(1) if m.group(1) is not None else m.group(2) or ""), m.start()


def symbol_index(texts, active):
    """Name by which another artifact can refer to a file (class, module, function) -> file; a name declared in more than one file is dropped (ambiguous)."""
    idx, dup = {}, set()
    for f, t in texts.items():
        name = eco.ecosystem_of(f, active)
        if not name:
            continue
        for sym, _kind in eco.ECOSYSTEMS[name]["symbols"](f, t):
            if sym in idx and idx[sym] != f:
                dup.add(sym)
            idx.setdefault(sym, f)
    return {k: v for k, v in idx.items() if k not in dup}


def class_index(texts):
    """fully qualified class name -> file, from the package line and the file name."""
    idx = {}
    for f, t in texts.items():
        if f.endswith(".java"):
            m = re.search(r"^\s*package\s+([\w.]+)\s*;", t, re.M)
            idx[(m.group(1) + "." if m else "") + Path(f).stem] = f
    return idx


# ---------------------------------------------------------------- XML wiring

XML_CLASS = [("class", re.compile(r'\b(?:class|factory-class|value-type|ref-class)\s*=\s*"([\w.$]+)"')),
             ("class name", re.compile(r'<class\s+name\s*=\s*"([\w.$]+)"')),
             ("web.xml", re.compile(r"<(?:servlet|filter|listener)-class>\s*([\w.$]+)\s*<"))]


def wiring(texts, classes, edges, report):
    mappings = collections.defaultdict(set)              # servlet class file -> url patterns
    for f, t in texts.items():
        if not f.endswith(".xml"):
            continue
        for label, rx in XML_CLASS:
            for m in rx.finditer(t):
                target = classes.get(m.group(1).split("$")[0])
                if target:
                    edges.add(f, target, "xml-class", "structure", "verified by syntax", f"{label} `{m.group(1)}` (line {line_of(t, m.start())})")
        try:
            root = ET.fromstring(t)
        except ET.ParseError:
            report["unparsed_xml"].append(f)
            continue
        tag = local(root.tag)
        if tag == "beans":
            bean_refs(f, root, classes, edges)
        elif tag == "web-app":
            web_xml(f, root, classes, mappings)
        elif tag == "hibernate-mapping":
            orm(f, root, classes, edges)
    return mappings


def bean_refs(f, root, classes, edges):
    by_id = {}
    for el in root.iter():
        if local(el.tag) == "bean" and el.get("class") and (el.get("id") or el.get("name")):
            by_id[el.get("id") or el.get("name")] = el.get("class")
    for bean in root.iter():
        if local(bean.tag) != "bean" or not bean.get("class") or bean.get("class").split("$")[0] not in classes:
            continue
        src = classes[bean.get("class").split("$")[0]]
        for el in bean.iter():
            for attr in ("ref", "bean", "local"):
                ref = el.get(attr)
                target = classes.get(by_id.get(ref, "").split("$")[0]) if ref else None
                if target:
                    edges.add(src, target, "bean-ref", "structure", "verified by syntax", f"bean `{ref}` referenced in {f}")


def web_xml(f, root, classes, mappings):
    name_class, name_urls = {}, collections.defaultdict(set)
    for el in root:
        t = local(el.tag)
        if t == "servlet":
            n, c = (el.findtext(x) or "" for x in ("{*}servlet-name", "{*}servlet-class"))
            if not n:
                n, c = ((el.find(x).text or "").strip() if el.find(x) is not None else "" for x in ("servlet-name", "servlet-class"))
            if n and c:
                name_class[n.strip()] = c.strip()
        elif t == "servlet-mapping":
            n = (el.findtext("{*}servlet-name") or el.findtext("servlet-name") or "").strip()
            for u in list(el.findall("{*}url-pattern")) + list(el.findall("url-pattern")):
                if u.text:
                    name_urls[n].add(u.text.strip())
    for n, c in name_class.items():
        target = classes.get(c.split("$")[0])
        if target:
            mappings[target] |= name_urls.get(n, set())


def orm(f, root, classes, edges):
    for cls in root.iter():
        if local(cls.tag) != "class" or not cls.get("name") or cls.get("name").split("$")[0] not in classes:
            continue
        src = classes[cls.get("name").split("$")[0]]
        for el in cls.iter():
            if el is cls:
                continue
            c = el.get("class") or el.get("entity-name")
            if c and c.split("$")[0] in classes:
                edges.add(src, classes[c.split("$")[0]], "orm-relation", "structure", "verified by syntax", f"<{local(el.tag)} class=\"{c}\"> in {f}")


# ---------------------------------------------------------------- URL links

def routes(texts, active, mappings, cfg):
    """Routes declared in code (Flask, Django, Express, Sinatra, Slim, Laravel, Spring annotations): handler file -> its static URL prefixes.
    A route declared in a test is not an endpoint of the application. Returns the patterns that came from a declaration (named with a leading slash elsewhere)."""
    skip = [re.compile(x) for x in cfg["url_links"]["ignore_route_sources"]]
    declared = set()
    for f, t in texts.items():
        name = eco.ecosystem_of(f, active)
        if not name or any(x.search(f) for x in skip):
            continue
        for rx in eco.ECOSYSTEMS[name]["routes"]:
            for m in rx.finditer(t):
                url = re.split(r"[<:{*(\[]", m.group("url"))[0]
                if url:
                    mappings[f].add(url)
                    declared.add(url.strip("/"))
    return declared


GENERIC = re.compile(r"[a-z]+")


def url_links(texts, mappings, edges, cfg, report, declared=frozenset()):
    c = cfg["url_links"]
    ignore = set(c["ignore_patterns"])
    patterns = {}                                         # cleaned pattern -> servlet file
    for cls_file, urls in mappings.items():
        for u in urls:
            core = u.strip("/")
            if u in ignore or "*" in core or "." in core.rsplit("/", 1)[-1] or len(core) < c["min_pattern_length"]:
                report["skipped_patterns"] += 1
                continue
            patterns[core] = cls_file
    if not patterns:
        return
    from_xml = {p for p in patterns if p not in declared}
    rx = rx_slash = None
    if from_xml:                                          # web.xml: `ListStudy`, with or without the slash
        alt = "|".join(re.escape(p) for p in sorted(from_xml, key=len, reverse=True))
        rx = re.compile(rf"""["'(/=]({alt})(?=[?"'&)#\s;]|$)""")
    if declared & set(patterns):                          # declared in code: used with the slash
        alt = "|".join(re.escape(p) for p in sorted(declared & set(patterns), key=len, reverse=True))
        rx_slash = re.compile(rf"""(?<![\w.:/])/({alt})(?=[?"'&)#\s;/]|$)""")
    skip_src = [re.compile(x) for x in c.get("ignore_sources", [])]
    found = {}
    for f, t in texts.items():
        if f.endswith((".xml", ".sql", ".properties", ".txt")) or (f in mappings and f.endswith(".java")) or any(x.search(f) for x in skip_src):
            continue
        hits = {}
        for r_ in (rx, rx_slash):
            for m in (r_.finditer(t) if r_ else ()):
                hits.setdefault(m.group(1), [line_of(t, m.start()), 0])[1] += 1
        for p, (line, n) in hits.items():
            found.setdefault(p, []).append((f, line, n))
    for p, uses in found.items():
        if GENERIC.fullmatch(p) and len(uses) > c["max_generic_sources"]:   # `study`, `form`, `login`: an ordinary word, not a link
            report["generic_urls"].append((p, len(uses)))
            continue
        for f, line, n in uses:
            edges.add(f, patterns[p], "url-link", "structure", "heuristic", f"names `{p}` (line {line})", n)


# ---------------------------------------------------------------- tables

DEFINE = [re.compile(r"\b(?:create|alter)\s+table\s+(?:if\s+not\s+exists\s+)?(?:\w+\.)?\"?`?(\w+)", re.I),
          re.compile(r"""\b(?:create_table|createTable|Schema::create|op\.create_table|schema\.createTable|\$table->create)\s*\(?\s*[:'"`]+(\w+)"""),
          re.compile(r"""\b(?:add_column|change_table|drop_table)\s*\(?\s*[:'"]+(\w+)""")]


def tables(texts, edges, cfg, report):
    c = cfg["tables"]
    defined = collections.defaultdict(set)               # table -> files that create or alter it
    definers = set()
    for f, t in texts.items():
        if f.endswith(".xml") and "<databaseChangeLog" in t:
            for m in re.finditer(r'tableName\s*=\s*"(\w+)"', t):
                defined[m.group(1).lower()].add(f)
                definers.add(f)
        elif f.endswith(".sql") or "migrat" in f.lower():
            for rx in DEFINE:
                for m in rx.finditer(t):
                    defined[m.group(1).lower()].add(f)
                    definers.add(f)
    names = {n for n in defined if len(n) >= c["min_name_length"] and n not in set(c["skip_names"])}
    report["tables_defined"], report["tables_ignored"] = len(defined), len(defined) - len(names)
    for n in names:
        for f in defined[n]:
            edges.add(f"table:{n}", f, "table-defined-in", "structure", "verified by syntax", "create table / migration")
    if not names:
        return
    alt = "|".join(re.escape(n) for n in sorted(names, key=len, reverse=True))
    ctx = re.compile(rf'\b(?:{c["context"]})\s+(?:\w+\.)?"?({alt})\b', re.I)
    annot = re.compile(rf"""(?:@Table\s*\(\s*name\s*=|\btable\s*=|\b__tablename__\s*=|\bdb_table\s*=|\btable_name\s*=|\$table\s*=)\s*["']({alt})["']""", re.I)
    for f, t in texts.items():
        if f in definers:
            continue                                      # definitions, not uses
        hits = {}
        for rx in (ctx, annot):
            for m in rx.finditer(t):
                hits.setdefault(m.group(1).lower(), [line_of(t, m.start()), 0])[1] += 1
        for n, (line, k) in hits.items():
            edges.add(f, f"table:{n}", "data-table", "structure", "heuristic", f"SQL or mapping names `{n}` (line {line})", k)


# ---------------------------------------------------------------- strings, bean lookups, dynamic sites

CANDIDATE = re.compile(r"[A-Za-z_][\w$]*(?:(?:\\{1,2}|::|[.:])[A-Za-z_][\w$]*)+")
SEPARATOR = re.compile(r"\\{1,2}|::|[.:]")


def resolve(token, names):
    """The file a dotted, colon or backslash separated name refers to: the whole token, else the token without its last one or two segments (`a.b.C.method`)."""
    token = token.replace("\\\\", "\\").split("$")[0]
    for _ in range(3):
        if token in names:
            return token, names[token]
        cut = [m.start() for m in SEPARATOR.finditer(token)]
        if len(cut) < 2:                                  # cutting would leave one segment: `flask.palletsprojects.com` is not `flask`
            return None, None
        token = token[:cut[-1]]
    return None, None


def string_classes(texts, names, edges, active):
    """A class, module or function named by its qualified name as text. In code only a whole string literal counts; in data files (XML, JSON, TOML, YAML, ...) any token."""
    for f, t in texts.items():
        if is_code(f, active):
            found = ((lit, off) for lit, off in literals(f, t, active) if CANDIDATE.fullmatch(lit))
            where = "string literal in code"
        else:
            found = ((m.group(0), m.start()) for m in CANDIDATE.finditer(t))
            where = "text"
        for tok, off in found:
            name, target = resolve(tok, names)
            if not target or target == f or (f, target, "xml-class") in edges.rows:
                continue
            edges.add(f, target, "string-class", "structure", "verified by name", f"`{name}` as {where} (line {line_of(t, off)})")


def bean_ids(texts, classes):
    ids = {}
    for f, t in texts.items():
        if f.endswith(".xml"):
            for m in re.finditer(r'<bean\b[^>]*?\b(?:id|name)\s*=\s*"([\w.-]+)"[^>]*?\bclass\s*=\s*"([\w.$]+)"', t, re.S):
                if m.group(2).split("$")[0] in classes:
                    ids[m.group(1)] = classes[m.group(2).split("$")[0]]
            for m in re.finditer(r'<bean\b[^>]*?\bclass\s*=\s*"([\w.$]+)"[^>]*?\b(?:id|name)\s*=\s*"([\w.-]+)"', t, re.S):
                if m.group(1).split("$")[0] in classes:
                    ids[m.group(2)] = classes[m.group(1).split("$")[0]]
    return ids


def lookups(texts, ids, edges, cfg, report, classes):
    calls = "|".join(cfg["dynamic_lookups"]["calls"])
    call = re.compile(rf"\.(?P<name>{calls})\s*\(\s*(?P<arg>[^)\n]*)")
    packages = collections.defaultdict(list)                       # "a.b.c." -> class files in that package
    for fq, cf in classes.items():
        packages[fq.rsplit(".", 1)[0] + "."].append(cf)
    prefix_lit = re.compile(r'"((?:[a-z_]\w*\.)+[a-z_]\w*)\.?"')                # a package name as a string, with or without the closing dot
    lookup = re.compile(r'(?:\bgetBean\s*\(\s*|@Qualifier\s*\(\s*|@Resource\s*\(\s*name\s*=\s*)"([\w.-]+)"')
    for f, t in texts.items():
        if not f.endswith(".java"):
            continue
        for m in lookup.finditer(t):
            if m.group(1) in ids:
                edges.add(f, ids[m.group(1)], "bean-lookup", "structure", "verified by name", f"bean id `{m.group(1)}` (line {line_of(t, m.start())})")
        for m in call.finditer(t):
            name, arg = m.group("name"), m.group("arg").strip()
            first = arg.split(",")[0].strip()
            if (not first or re.fullmatch(r'"[^"]*"', first) or first.endswith(".class") or re.fullmatch(r"[A-Z][A-Z0-9_]*", first)):
                continue                                  # a literal (resolved elsewhere), a type, a constant, or a getter without an argument
            if name in ("getField", "getMethod", "getDeclaredField", "getDeclaredMethod") and "java.lang.reflect" not in t and ".getClass()" not in t:
                continue                                  # a method of another API with the same name
            if name in ("forName", "loadClass"):
                for pm in prefix_lit.finditer(t):
                    for target in packages.get(pm.group(1) + ".", ()):
                        edges.add(f, target, "prefix-class", "structure", "heuristic",
                                  f"package prefix `{pm.group(1)}` and a name built at run time in `.{name}({arg[:30]})` (line {line_of(t, m.start())})")
            edges.add(f, f"dynamic:{name}", "dynamic-site", "evidence", "verified by syntax",
                      f"`.{name}({arg[:40]})` (line {line_of(t, m.start())})")


def dynamic_sites(texts, active, edges, cfg):
    """Names built or looked up at run time, outside Java: the call and its argument are not a plain string literal."""
    literal_arg = re.compile(r"""^\s*(?:[rbuf]?"[^"]*"|[rbuf]?'[^']*'|:\w+|`[^`$]*`)\s*(?:[,)]|$)""")
    resolvable = re.compile(r"(?:File\.|__dir__|__FILE__|__dirname|dirname\(|path\.(?:join|resolve)|\$this\b|\bstatic\b|\bself\b)")
    skip = [re.compile(x) for x in cfg["dynamic_lookups"].get("ignore_sources", [])]
    for f, t in texts.items():
        name = eco.ecosystem_of(f, active)
        if not name or name == "java" or any(x.search(f) for x in skip):
            continue
        for label, rx in eco.ECOSYSTEMS[name]["dynamic"]:
            for m in rx.finditer(t):
                arg = m.group("arg").strip()
                start = t.rfind("\n", 0, m.start()) + 1
                if t[start:m.start()].lstrip().startswith(("#", "//", "*", "/*")):
                    continue                                   # a comment
                if not arg or literal_arg.match(arg + ")") or resolvable.search(arg):
                    continue
                edges.add(f, f"dynamic:{label}", "dynamic-site", "evidence", "verified by syntax", f"`{m.group(0).strip()[:60]}` (line {line_of(t, m.start())})")


# ---------------------------------------------------------------- names (connascence of name)

WORDS = re.compile(r"[A-Z][a-z0-9]*|[a-z0-9]+")             # the words of a camelCase or snake_case identifier


def names(texts, classes, edges, cfg, report, active):
    c = cfg["names"]
    declared = collections.defaultdict(set)
    for f, t in texts.items():
        lang = eco.ecosystem_of(f, active)
        if not lang:
            continue
        cand = {Path(f).stem}
        for i, rx in enumerate(eco.ECOSYSTEMS[lang]["decl"]):
            for m in rx.finditer(t):
                n = m.group(1)
                cand.add(n[0].lower() + n[1:] if lang == "java" and i == 0 else n)
        for n in cand:
            if len(n) >= c["min_length"] and len(WORDS.findall(n)) >= c["min_humps"]:
                declared[n].add(f)
    declared = {n: fs for n, fs in declared.items() if len(fs) <= c["max_declaring_files"] and n not in set(c["skip"])}
    report["names_candidates"] = len(declared)
    if not declared:
        return
    rx = re.compile(r"\b(" + "|".join(re.escape(n) for n in sorted(declared, key=len, reverse=True)) + r")\b")
    spread = collections.defaultdict(lambda: collections.defaultdict(set))      # name -> artifact kind -> files
    found = collections.defaultdict(dict)                                      # name -> file -> [line, count]
    for f, t in texts.items():
        kind = f.rsplit(".", 1)[-1]
        for m in rx.finditer(t):
            n = m.group(1)
            if f in declared[n]:
                continue
            if is_code(f, active) and eco.ecosystem_of(f, active) in {eco.ecosystem_of(d, active) for d in declared[n]}:   # same language: only a whole string literal crosses a boundary
                quotes = '"' if eco.ECOSYSTEMS[eco.ecosystem_of(f, active)].get("double_quotes_only") else "\"'"
                before, after = t[m.start() - 1:m.start()], t[m.end():m.end() + 1]
                if before != after or before not in quotes or not before:
                    continue
            spread[n][kind].add(f)
            e = found[n].setdefault(f, [line_of(t, m.start()), 0])
            e[1] += 1
    hubs = []
    for n, kinds in spread.items():
        files = set().union(*kinds.values())
        if len(files) > c["max_spread_files"]:
            hubs.append((n, len(files), {k: len(v) for k, v in kinds.items()}))
            continue
        for f, (line, k) in found[n].items():
            for target in declared[n]:
                edges.add(f, target, "name-link", "structure", "heuristic", f"`{n}` (line {line})", k)
    report["name_hubs"] = sorted(hubs, key=lambda h: -h[1])[:12]


# ---------------------------------------------------------------- file names and keys

def shared_depth(a, b):
    """Number of leading path segments two repo paths have in common."""
    n = 0
    for x, y in zip(a.split("/")[:-1], b.split("/")[:-1]):
        if x != y:
            break
        n += 1
    return n


def file_names(texts, edges, cfg, report):
    c = cfg["file_names"]
    exts = tuple("." + e for e in (c["extensions"] if c["extensions"] != "auto" else {f.rsplit(".", 1)[-1] for f in texts if "." in f.rsplit("/", 1)[-1]}))
    by_base = collections.defaultdict(list)
    for f in texts:
        if f.endswith(exts) and len(Path(f).name) >= c["min_name_length"]:
            by_base[Path(f).name].append(f)
    if not by_base:
        return
    generic = {b for b, fs in by_base.items() if len(fs) > c["max_same_name"]}              # `index.js`, `__init__.py`: no way to tell which one is meant
    report["generic_file_names"] = sorted(generic)
    for b in generic:
        del by_base[b]
    if not by_base:
        return
    alt = "|".join(re.escape(b) for b in sorted(by_base, key=len, reverse=True))
    rx = re.compile(rf"""["']((?:[\w.${{}}\-]+/)*)({alt})["'?#]""")             # an optional directory part, then the file name
    for f, t in texts.items():
        for m in rx.finditer(t):
            base = m.group(2)
            targets = [x for x in by_base[base] if x != f]
            via_path = False
            parts = [p_ for p_ in m.group(1).split("/") if p_ and not p_.startswith("$") and p_ not in (".", "..")]
            if len(targets) > 1 and parts:                    # the text names a directory too: `include/footer.jsp` is not `login-include/footer.jsp`
                tail = "/".join(parts + [base])
                narrowed = [x for x in targets if x == tail or x.endswith("/" + tail)]
                if narrowed:
                    targets, via_path = narrowed, True
            if len(targets) > 1:                              # still several (web and ws): keep the nearest one to the source
                best = max(shared_depth(f, x) for x in targets)
                targets = [x for x in targets if shared_depth(f, x) == best]
            same_name = len(by_base[base])
            conf = "verified by name" if same_name <= 1 else "verified by name and path" if via_path and len(targets) == 1 else f"heuristic (nearest of {same_name} files with this name)"
            for target in targets:
                edges.add(f, target, "file-name", "structure", conf, f"names the file `{m.group(1)}{base}` (line {line_of(t, m.start())})")


KEY_CODE = re.compile(r"""["']([A-Za-z][A-Za-z0-9_.\-]{7,})["']""")
KEY_DATA = [re.compile(r">\s*([A-Za-z][A-Za-z0-9_.\-]{7,})\s*<"), re.compile(r'="([A-Za-z][A-Za-z0-9_.\-]{7,})"'),
            re.compile(r"^\s*([A-Za-z][A-Za-z0-9_.\-]{7,})\s*[=:]", re.M), re.compile(r'"([A-Za-z][A-Za-z0-9_.\-]{7,})"\s*:')]
KEY_VIEW = re.compile(r"\b([A-Za-z][A-Za-z0-9_]{7,})\b")


def keys(texts, classes, edges, cfg, active):
    c = cfg["keys"]
    view_ext = tuple("." + e for e in c.get("view_extensions", []))
    code, data, view = collections.defaultdict(dict), collections.defaultdict(dict), collections.defaultdict(dict)       # key -> file -> line
    fq = set(classes)
    keylike = lambda k: len(k) >= c["min_length"] and re.search(r"[a-z][A-Z]|_|\d", k)        # camelCase, snake_case or a digit inside: not a plain word, however capitalised
    skip_src = [re.compile(x) for x in c.get("ignore_sources", [])]
    for f, t in texts.items():
        if is_code(f, active):
            for m in KEY_CODE.finditer(t):
                k = m.group(1)
                if keylike(k) and k not in fq and not k.startswith(("org.", "com.", "java.", "javax.")):
                    code[k].setdefault(f, line_of(t, m.start()))
        elif f.endswith((".xml", ".properties", ".json", ".yml", ".yaml", ".toml", ".cfg", ".ini")):
            for rx in KEY_DATA:
                for m in rx.finditer(t):
                    if keylike(m.group(1)):
                        data[m.group(1)].setdefault(f, line_of(t, m.start()))
        if view_ext and f.endswith(view_ext) and not any(x.search(f) for x in skip_src) and not f.endswith((".xml", ".properties", ".json", ".yml", ".yaml")):
            for m in KEY_VIEW.finditer(t):
                if keylike(m.group(1)):
                    view[m.group(1)].setdefault(f, line_of(t, m.start()))
    for k in set(code) & set(data):
        if len(code[k]) > c["max_code_files"] or len(data[k]) > c["max_data_files"]:
            continue
        for cf, cl in code[k].items():
            for df, dl in data[k].items():
                edges.add(cf, df, "key-link", "structure", "heuristic", f"`{k}` in code (line {cl}) and in the data file (line {dl})")
    for k in set(code) & set(view):                                  # the view depends on the code that sets the key
        if len(code[k]) > c["max_code_files"] or len(view[k]) > c["max_data_files"]:
            continue
        for cf, cl in code[k].items():
            for vf, vl in view[k].items():
                if eco.ecosystem_of(vf, active) and eco.ecosystem_of(vf, active) == eco.ecosystem_of(cf, active):
                    continue                                  # a script and code of the same language: a plain string, not a view reading a key
                edges.add(vf, cf, "key-link", "structure", "heuristic", f"`{k}` in the view (line {vl}) and set or read in code (line {cl})")


# ---------------------------------------------------------------- co-change

def co_change(repo, texts, edges, cfg, report):
    c = cfg["co_change"]
    args = ["log", "--no-merges", "--name-only", "--format=\x1e%aI"]
    if c["since_months"]:
        last = git(repo, "log", "-1", "--no-merges", "--format=%aI", "--", *texts).strip()
        if last:
            args.insert(1, "--since=" + (dt.datetime.fromisoformat(last) - dt.timedelta(days=30 * c["since_months"])).isoformat())
    out = git(repo, *args)
    own, pairs, used, skipped = collections.Counter(), collections.Counter(), 0, 0
    for chunk in out.split("\x1e")[1:]:
        files = sorted({n for n in chunk.split("\n")[1:] if n in texts})
        if not files:
            continue
        if len(files) > c["max_files_per_commit"]:
            skipped += 1
            continue
        used += 1
        own.update(files)
        pairs.update(itertools.combinations(files, 2))
    report["commits_used"], report["commits_skipped"] = used, skipped
    for (a, b), n in pairs.items():
        if n < c["min_commits_together"]:
            continue
        ca, cb = n / own[a], n / own[b]
        if max(ca, cb) >= c["min_confidence"] and min(ca, cb) >= c["min_confidence"] / 2:
            edges.add(a, b, "co-change", "evidence", "heuristic", f"{n} commits together ({ca:.0%} of {Path(a).name}, {cb:.0%} of {Path(b).name})", n)


# ---------------------------------------------------------------- output

def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["source", "target", "kind", "layer", "confidence", "evidence", "weight"])
        for r in sorted(rows, key=lambda r: (r["kind"], r["source"], r["target"])):
            w.writerow([r[k] for k in ("source", "target", "kind", "layer", "confidence", "evidence", "weight")])


def write_md(path, rows, meta, report, classes, cfg):
    by = collections.defaultdict(list)
    for r in rows:
        by[r["kind"]].append(r)
    L = ["# Dependencies across artifacts\n",
         f"Generated {meta['generated']} · commit `{meta['commit']}` · {meta['files']} files scanned ({meta['skipped']} too large, skipped) · ecosystems: {meta['ecosystems']}\n",
         "> What a language tool does not see: names spelled the same in different artifacts, classes and modules named as strings, URLs between templates and the routes that serve them, shared database tables, files that change together. "
         "**structure** edges say \"source depends on target\"; **evidence** edges (co-change) only say that files changed together and prove nothing by themselves. "
         "Every edge names its evidence; confidence is `verified by syntax` or `heuristic`.\n",
         "## Edges per kind\n", "| Kind | Layer | Edges | Sources | Targets | Confidence |", "|---|---|---:|---:|---:|---|"]
    for k in KINDS:
        rs = by.get(k, [])
        if rs:
            L.append(f"| `{k}` | {rs[0]['layer']} | {len(rs)} | {len({r['source'] for r in rs})} | {len({r['target'] for r in rs})} | {rs[0]['confidence']} |")
        else:
            L.append(f"| `{k}` | – | 0 | 0 | 0 | – |")
    for k in KINDS:
        rs = by.get(k, [])
        if not rs:
            continue
        indeg = collections.Counter(r["target"] for r in rs)
        L += ["", f"## `{k}`\n", "Most depended on (targets with the most sources): " + ", ".join(f"`{t}` {n}" for t, n in indeg.most_common(5)), "", "Examples:"]
        L += [f"- `{r['source']}` → `{r['target']}`: {r['evidence']}" for r in sorted(rs, key=lambda r: -r["weight"])[:4]]
    java = [f for f in classes.values()]
    wired = {r["target"] for r in by.get("xml-class", [])}
    linked = {r["target"] for r in by.get("url-link", [])}
    L += ["", "## Coverage\n",
          *([f"- Java classes named in XML: {len(wired)} of {len(java)}"] if java else []),
          f"- Handlers with a URL link found: {len(linked)} of {report['servlets_mapped']} that serve a route",
          f"- Tables: {report['tables_defined']} defined, {report['tables_ignored']} ignored (name too short or skipped), "
          f"{len({r['target'] for r in by.get('data-table', [])})} used by name",
          f"- Mapping patterns skipped (wildcards, extensions, too short): {report['skipped_patterns']}",
          f"- Git: {report.get('commits_used', 0)} commits used, {report.get('commits_skipped', 0)} larger than "
          f"{cfg['co_change']['max_files_per_commit']} files left out"]
    if report["unparsed_xml"]:
        L.append(f"- XML files that could not be parsed (class names were still matched by text): {len(report['unparsed_xml'])}, e.g. `{report['unparsed_xml'][0]}`")
    dyn = collections.Counter(r["source"] for r in by.get("dynamic-site", []))
    if dyn:
        L += ["", "## Where names are built at run time\n",
              f"{len(dyn)} files call reflection or look names up with a computed argument. A change near them can reach further than any list here shows: the radius is a lower bound.",
              ""] + [f"- `{f}`: {n} site(s)" for f, n in dyn.most_common(8)]
    if report["name_hubs"]:
        L += ["", "## Names shared widely across artifacts (hubs, no edges)\n",
              f"Identifiers declared in a few classes and spelled the same in many other files ({report['names_candidates']} candidates were checked). "
              "A change of such a name touches every file listed, in every kind of artifact; no edges are written because the list would drown the rest.", "",
              "| Name | Files | By file type |", "|---|---:|---|"]
        L += [f"| `{n}` | {k} | " + ", ".join(f"{t} {v}" for t, v in sorted(kinds.items(), key=lambda kv: -kv[1])) + " |" for n, k, kinds in report["name_hubs"]]
    L += ["", "## Not covered\n",
          "- Properties keys and message bundle keys read by code, feature flags (only names that happen to be declared as identifiers are found).",
          "- What a computed name resolves to at run time: dynamic sites are listed, their targets are not known.",
          "- Identifiers stored only in a database's run-time data: seed data and changelogs in the repository are scanned, the live data is not.",
          "- Dependency injection by type or annotation scanning (`@Autowired`, component scan, framework auto-wiring): only what is spelled out is found.",
          "- Calls between systems (REST clients, queues, scheduled jobs, files exchanged).",
          "- Everything the heuristic kinds miss or over-match: a table name or URL in an ordinary text is a chance hit. Treat `heuristic` edges as leads."]
    path.write_text("\n".join(L) + "\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", default=".")
    ap.add_argument("--out", default=None, help="default <repo>/temp/dependency-map")
    ap.add_argument("--config", default=None, help="overrides for this repository, merged over the defaults (dependency-map.yaml of the skill)")
    a = ap.parse_args()
    repo = Path(a.repo).resolve()
    out = Path(a.out).resolve() if a.out else repo / "temp" / "dependency-map"
    cfg = settings.load(a.config)
    out.mkdir(parents=True, exist_ok=True)

    texts, skipped, active = read_texts(repo, cfg)
    print("ecosystems: " + (", ".join(f"{n} ({k} code files)" for n, k in active.items()) or "none found") + f"; {len(texts)} files in scope", file=sys.stderr)
    classes = class_index(texts)
    symbols = symbol_index(texts, active)
    edges = Edges()
    report = {"generic_urls": [], "unparsed_xml": [], "skipped_patterns": 0, "tables_defined": 0, "tables_ignored": 0, "servlets_mapped": 0, "names_candidates": 0, "name_hubs": []}
    mappings = wiring(texts, classes, edges, report) if cfg["wiring"]["enabled"] else {}
    mappings = collections.defaultdict(set, mappings)
    declared = routes(texts, active, mappings, cfg)
    report["servlets_mapped"] = len(mappings)
    if cfg["url_links"]["enabled"]:
        url_links(texts, mappings, edges, cfg, report, declared)
    if cfg["tables"]["enabled"]:
        tables(texts, edges, cfg, report)
    if cfg["string_classes"]["enabled"]:
        string_classes(texts, {**symbols, **classes}, edges, active)
    if cfg["dynamic_lookups"]["enabled"]:
        lookups(texts, bean_ids(texts, classes), edges, cfg, report, classes)
        dynamic_sites(texts, active, edges, cfg)
    if cfg["file_names"]["enabled"]:
        file_names(texts, edges, cfg, report)
    if cfg["keys"]["enabled"]:
        keys(texts, {**symbols, **classes}, edges, cfg, active)
    if cfg["names"]["enabled"]:
        names(texts, classes, edges, cfg, report, active)
    if cfg["co_change"]["enabled"]:
        co_change(repo, texts, edges, cfg, report)

    rows = list(edges.rows.values())
    meta = {"generated": dt.datetime.now().replace(microsecond=0).isoformat(), "commit": git(repo, "rev-parse", "--short", "HEAD").strip(),
            "files": len(texts), "skipped": skipped, "ecosystems": ", ".join(active) or "none found"}
    write_csv(out / "dependencies.csv", rows)
    write_md(out / "dependencies.md", rows, meta, report, classes, cfg)
    cnt = collections.Counter(r["kind"] for r in rows)
    print(f"{len(rows)} edges: " + ", ".join(f"{k} {cnt[k]}" for k in KINDS if cnt[k]) + f" -> {out}")


if __name__ == "__main__":
    main()
