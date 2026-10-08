"""Per-language knowledge of dependency-map: what a source file declares, how a string names it, where URLs are routed, where names are built at run time.

The kinds of dependency are the same everywhere; only these profiles differ. A profile is plain data (regular expressions) plus two small functions, so a language
can be added here without touching the scanner. Provenance: [own], derived from how the frameworks name things, checked on small public repositories.
"""
import re
from pathlib import Path

# ---------------------------------------------------------------- symbols: which names does a file declare?
# A symbol is a name by which other artifacts (strings, configuration, templates) can refer to the file: a class, a module, a function.


def _java(f, t):
    m = re.search(r"^\s*package\s+([\w.]+)\s*;", t, re.M)
    return [((m.group(1) + "." if m else "") + Path(f).stem, "class")]


def _python_module(f):
    """Dotted module path of a .py file: climb while the folder is a package (has __init__.py is unknown here, so the first folder without a dot-safe name or a known root ends it)."""
    parts = f[:-3].split("/")
    if parts[-1] == "__init__":
        parts = parts[:-1]
    while parts and parts[0] in ("src", "lib", "source", "python"):
        parts = parts[1:]
    return ".".join(parts)


def _python(f, t):
    mod = _python_module(f)
    out = [(mod, "module")] if mod else []
    for m in re.finditer(r"^(?:class|def|async\s+def)\s+([A-Za-z_]\w*)", t, re.M):
        if mod:
            out.append((f"{mod}.{m.group(1)}", "symbol"))
            out.append((f"{mod}:{m.group(1)}", "symbol"))
    return out


def _php(f, t):
    ns = re.search(r"^\s*namespace\s+([\w\\]+)\s*;", t, re.M)
    prefix = (ns.group(1) + "\\") if ns else ""
    return [(prefix + m.group(1), "class") for m in re.finditer(r"^\s*(?:(?:final|abstract|readonly)\s+)*(?:class|interface|trait|enum)\s+([A-Za-z_]\w*)", t, re.M)]


def _ruby(f, t):
    out, stack = [], []
    for line in t.splitlines():
        m = re.match(r"^(\s*)(?:class|module)\s+([A-Z]\w*(?:::[A-Z]\w*)*)", line)
        if m:
            indent = len(m.group(1))
            while stack and stack[-1][0] >= indent:
                stack.pop()
            stack.append((indent, m.group(2)))
            out.append(("::".join(n for _, n in stack), "class"))
    return out


def _js(f, t):
    return []                                        # modules are files: reached by path (file-name), not by a declared name


def _c(f, t):
    return []


# ---------------------------------------------------------------- the profiles

ECOSYSTEMS = {
    "java": {
        "code_ext": ("java",),
        "double_quotes_only": True,
        "symbols": _java,
        "routes": [re.compile(r'@(?:WebServlet|RequestMapping|GetMapping|PostMapping|PutMapping|DeleteMapping|PatchMapping)\s*\(\s*(?:value\s*=\s*|urlPatterns\s*=\s*)?\{?\s*"(?P<url>/[^"]*)"')],
        "dynamic": r"\.(?:forName|loadClass|getBean|getMethod|getDeclaredMethod|getField|getDeclaredField)\s*\(",   # handled by a dedicated, tuned rule in the scanner
        "decl": [re.compile(r"\b(?:public|protected)\s+[\w<>\[\],.? ]+?\s+(?:get|is)([A-Z]\w*)\s*\(\s*\)"),
                 re.compile(r"\bprivate\s+(?:static\s+)?(?:final\s+)?[\w<>\[\],.? ]+?\s+([a-z]\w*)\s*(?:=|;)")],
    },
    "python": {
        "code_ext": ("py",),
        "symbols": _python,
        "routes": [re.compile(r"""@\w+(?:\.\w+)*\.(?:route|get|post|put|delete|patch|websocket)\(\s*['"](?P<url>/[^'"]*)"""),
                   re.compile(r"""\b(?:re_)?path\(\s*r?['"](?P<url>[^'"]+)['"]\s*,""")],
        "dynamic": [("import_module", re.compile(r"\b(?:importlib\.)?import_module\(\s*(?P<arg>[^)\n]*)")),
                    ("__import__", re.compile(r"\b__import__\(\s*(?P<arg>[^)\n]*)")),
                    ("getattr", re.compile(r"\bgetattr\(\s*[^,\n]+,\s*(?P<arg>[^,)\n]*)")),
                    ("setattr", re.compile(r"\bsetattr\(\s*[^,\n]+,\s*(?P<arg>[^,)\n]*)")),
                    ("eval", re.compile(r"(?<![\w.])(?:eval|exec)\(\s*(?P<arg>[^)\n]*)"))],
        "decl": [re.compile(r"^(?:class|def)\s+([A-Za-z_]\w*)", re.M)],
    },
    "php": {
        "code_ext": ("php",),
        "symbols": _php,
        "routes": [re.compile(r"""->(?:get|post|put|delete|patch|any|map|options)\(\s*(?:\[[^\]]*\]\s*,\s*)?['"](?P<url>/[^'"]*)"""),
                   re.compile(r"""\bRoute::(?:get|post|put|delete|patch|any|match)\(\s*(?:\[[^\]]*\]\s*,\s*)?['"](?P<url>/?[^'"]*)""")],
        "dynamic": [("new $class", re.compile(r"\bnew\s+(?P<arg>\$\w+)")),
                    ("call_user_func", re.compile(r"\bcall_user_func(?:_array)?\(\s*(?P<arg>[^)\n]*)")),
                    ("class_exists", re.compile(r"\b(?:class_exists|method_exists|function_exists|is_callable)\(\s*(?P<arg>[^),\n]*)")),
                    ("variable variable", re.compile(r"(?P<arg>\$\$\w+)")),
                    ("include variable", re.compile(r"\b(?:include|require)(?:_once)?\s*\(?\s*(?P<arg>\$\w+[^;\n]*)")),
                    ("$obj::", re.compile(r"(?P<arg>\$\w+)::\w+"))],
        "decl": [re.compile(r"\bfunction\s+([A-Za-z_]\w*)\s*\("), re.compile(r"^\s*(?:abstract\s+|final\s+)?class\s+([A-Za-z_]\w*)", re.M)],
    },
    "ruby": {
        "code_ext": ("rb", "rake", "ru"),
        "symbols": _ruby,
        "routes": [re.compile(r"""^\s*(?:get|post|put|delete|patch|options|head)\s*\(?\s*['"](?P<url>/[^'"]*)""", re.M),
                   re.compile(r"""\b(?:match|root)\s+['"](?P<url>/?[^'"]*)""")],
        "dynamic": [("const_get", re.compile(r"\bconst_get\(\s*(?P<arg>[^)\n]*)")),
                    ("constantize", re.compile(r"(?P<arg>[\w@.\"'#{}]+)\.constantize")),
                    ("send", re.compile(r"\b(?:public_)?send\(\s*(?P<arg>[^,)\n]*)")),
                    ("require", re.compile(r"\brequire(?:_relative)?\s+\(?(?P<arg>[^\n'\"][^\n]*)")),
                    ("eval", re.compile(r"\b(?:instance_|class_|module_)?eval\(?\s*(?P<arg>[^)\n]*)"))],
        "decl": [re.compile(r"^\s*def\s+(?:self\.)?([A-Za-z_]\w*[?!]?)", re.M), re.compile(r"^\s*(?:class|module)\s+([A-Z]\w*)", re.M)],
    },
    "javascript": {
        "code_ext": ("js", "mjs", "cjs", "jsx", "ts", "tsx"),
        "symbols": _js,
        "routes": [re.compile(r"""\b(?:app|router|server|api|\w+Router|\w+App)\.(?:get|post|put|delete|patch|all|use|route)\(\s*['"`](?P<url>/[^'"`]*)""")],
        "dynamic": [("require", re.compile(r"\brequire\(\s*(?P<arg>[^)\n]*)")),
                    ("import()", re.compile(r"(?<![\w.])import\(\s*(?P<arg>[^)\n]*)")),
                    ("eval", re.compile(r"(?<![\w.])(?:eval|new\s+Function)\(\s*(?P<arg>[^)\n]*)"))],
        "decl": [re.compile(r"\bfunction\s+([A-Za-z_$][\w$]*)\s*\("), re.compile(r"^\s*(?:export\s+)?(?:class)\s+([A-Za-z_$][\w$]*)", re.M),
],
    },
    "c": {
        "code_ext": ("c", "h", "cc", "cpp", "hpp", "cxx"),
        "double_quotes_only": True,
        "symbols": _c,
        "routes": [],
        "dynamic": [("dlopen/dlsym", re.compile(r"\b(?:dlopen|dlsym|LoadLibrary\w*|GetProcAddress)\(\s*(?P<arg>[^)\n]*)"))],
        "decl": [re.compile(r"^[A-Za-z_][\w\s\*]*?\b([a-z_]\w*)\s*\([^;{)]*\)\s*\{", re.M)],
    },
}

DATA_EXT = ("xml", "json", "yml", "yaml", "toml", "cfg", "ini", "properties", "sql", "csv", "html", "htm", "jsp", "tag", "ftl", "twig", "erb", "haml", "slim", "ejs",
            "pug", "jade", "hbs", "mustache", "phtml", "jinja", "j2", "txt", "mk", "cmake", "gemspec", "rake", "gradle")
CONFIG_NAMES = ("Makefile", "makefile", "CMakeLists.txt", "Rakefile", "Gemfile", "Dockerfile", "package.json", "composer.json", "pyproject.toml", "setup.py", "setup.cfg", "tox.ini")
VENDORED = r"(^|/)(node_modules|vendor|bower_components|third_party|3rdparty|deps|external|target|build|dist|out|__pycache__|\.venv|venv|site-packages)/"


def detect(paths, minimum=3):
    """Ecosystems with at least `minimum` code files among the tracked paths."""
    found = {}
    for name, p in ECOSYSTEMS.items():
        n = sum(1 for f in paths if f.rsplit(".", 1)[-1] in p["code_ext"] and "." in Path(f).name)
        if n >= minimum:
            found[name] = n
    return found


def code_ext_of(name):
    return ECOSYSTEMS[name]["code_ext"]


def ecosystem_of(path, active):
    ext = path.rsplit(".", 1)[-1] if "." in Path(path).name else ""
    for name in active:
        if ext in ECOSYSTEMS[name]["code_ext"]:
            return name
    return None
