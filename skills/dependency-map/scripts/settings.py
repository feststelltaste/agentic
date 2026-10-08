"""Settings of dependency-map: neutral defaults in dependency-map.yaml, plus an optional file of overrides for one repository.

The override file holds only what differs from the defaults (a vendored folder to ignore, a ticket pattern, a threshold). It is merged key by key over the defaults;
a list in the override replaces the list in the defaults.
"""
from pathlib import Path

import yaml

DEFAULTS = Path(__file__).resolve().parent.parent / "dependency-map.yaml"


def merge(base, over):
    out = dict(base)
    for k, v in (over or {}).items():
        out[k] = merge(base[k], v) if isinstance(v, dict) and isinstance(base.get(k), dict) else v
    return out


def load(override=None):
    cfg = yaml.safe_load(DEFAULTS.read_text())
    if override:
        cfg = merge(cfg, yaml.safe_load(Path(override).read_text()))
    return cfg


def files_in_scope(repo, cfg, git, extra_ignore=()):
    """-> (tracked files in scope, ecosystems found {name: code files}). Scope = code of the ecosystems found + data, template and configuration files."""
    import re

    import ecosystems as eco
    excl = [re.compile(x) for x in list(cfg["scope"]["exclude"]) + list(extra_ignore)]
    tracked = [f for f in git(repo, "ls-files", "-z").split("\0") if f]
    wanted = cfg["scope"].get("ecosystems", "auto")
    found = eco.detect([f for f in tracked if not any(x.search(f) for x in excl)])
    active = found if wanted == "auto" else {n: found.get(n, 0) for n in wanted}
    if cfg["scope"]["extensions"] == "auto":
        exts = set(eco.DATA_EXT) | {e for n in active for e in eco.code_ext_of(n)}
    else:
        exts = set(cfg["scope"]["extensions"])
    keep = [f for f in tracked if (f.rsplit(".", 1)[-1] in exts and "." in f.rsplit("/", 1)[-1] or f.rsplit("/", 1)[-1] in eco.CONFIG_NAMES)
            and not any(x.search(f) for x in excl)]
    return keep, active
