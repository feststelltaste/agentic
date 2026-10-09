"""Builds <name>.html from <name>.src.html:
  {{IMG:path}}    -> data: URI (png/jpg)
  {{CHART:name}}  -> inline SVG from charts.py (CHARTS = {"name": function_without_arguments}; colors via THEME["brand"] etc.)
  /*@@THEME@@*/   -> CSS of the theme (colors, font); {{FONT:file}} inside it -> data: URI from assets/fonts
Usage (in the article folder): python3 build.py <name> [theme]      theme can also be set via the THEME environment variable (default: default)
Themes are searched in: ./themes, ~/.config/repo-story/themes, <skill>/assets/themes. New theme: scripts/make-theme.py."""
import base64, os, pathlib, re, sys, importlib.util

HERE = pathlib.Path(__file__).resolve().parent
SKILL_ASSETS = pathlib.Path(os.environ["REPO_STORY_ASSETS"]) if os.environ.get("REPO_STORY_ASSETS") else next((p for p in (HERE, HERE.parent / "assets", *[q / "assets" for q in HERE.parents]) if (p / "themes").is_dir()), HERE)
THEME_NAME = (sys.argv[2] if len(sys.argv) > 2 else os.environ.get("THEME", "default"))
FONT_DIRS = [HERE / "fonts", pathlib.Path.home() / ".config/repo-story/fonts", SKILL_ASSETS / "fonts"]


def load_theme(name):
    for d in (HERE / "themes", pathlib.Path.home() / ".config/repo-story/themes", SKILL_ASSETS / "themes"):
        f = d / f"{name}.css"
        if f.exists():
            css = f.read_text(encoding="utf-8")
            return css, {k: v for k, v in re.findall(r"--([a-z0-9-]+):\s*(#[0-9a-fA-F]{6})", css)}
    sys.exit(f"Theme '{name}' not found (searched in ./themes, ~/.config/repo-story/themes, {SKILL_ASSETS / 'themes'})")


THEME_CSS, THEME = load_theme(THEME_NAME)


def font(m):
    for d in FONT_DIRS:
        if (d / m.group(1)).exists():
            return "data:font/ttf;base64," + base64.b64encode((d / m.group(1)).read_bytes()).decode()
    sys.exit(f"Font file {m.group(1)} not found in {[str(d) for d in FONT_DIRS]}")


BRAND, BRAND25, MUTED, LINE, ACCENT, ACCENT_INK = (THEME[k] for k in ("brand", "brand-25", "muted", "line", "accent", "accent-ink"))


def img(m):
    p = (HERE / m.group(1)).resolve()
    mime = "image/jpeg" if p.suffix.lower() in (".jpg", ".jpeg") else "image/png"
    return f"data:{mime};base64," + base64.b64encode(p.read_bytes()).decode()


def line_chart(points, ymin, ymax, ref=None, ref_label="", label="", W=660, H=230, L=44, R=92, T=18, B=40, step=False):
    """points: [(x_label, sub_label, value)], evenly spaced. ref: dashed reference line (e.g. 'all 258')."""
    Y = lambda v: T + (ymax - v) / (ymax - ymin) * (H - T - B)
    dx = (W - L - R - 40) / max(1, len(points) - 1)
    X = lambda i: L + 20 + i * dx
    o = [f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" aria-label="{label}">']
    for v in range(int(ymin), int(ymax) + 1, max(1, int((ymax - ymin) / 3))):
        o.append(f'<line x1="{L}" x2="{W-R}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" stroke="{LINE}"/>'
                 f'<text x="{L-8}" y="{Y(v)+3.5:.1f}" font-size="10" fill="{MUTED}" text-anchor="end">{v}</text>')
    if ref is not None:
        o.append(f'<line x1="{L}" x2="{W-R}" y1="{Y(ref):.1f}" y2="{Y(ref):.1f}" stroke="{BRAND25}" stroke-dasharray="3 3"/>'
                 f'<text x="{W-R+8}" y="{Y(ref)+3.5:.1f}" font-size="10" fill="{MUTED}">{ref_label}</text>')
    d = ""
    for i, (_, _, v) in enumerate(points):
        d += (f"M{X(i):.1f},{Y(v):.1f}" if i == 0 else (f" H{X(i):.1f} V{Y(v):.1f}" if step else f" L{X(i):.1f},{Y(v):.1f}"))
    o.append(f'<path d="{d}" fill="none" stroke="{BRAND}" stroke-width="2" stroke-linejoin="round"/>')
    for i, (a, b, v) in enumerate(points):
        o.append(f'<circle cx="{X(i):.1f}" cy="{Y(v):.1f}" r="4" fill="{BRAND}" stroke="#fff" stroke-width="2"/>'
                 f'<text x="{X(i):.1f}" y="{H-B+15}" font-size="10" font-weight="800" fill="{BRAND}" text-anchor="middle">{a}</text>'
                 f'<text x="{X(i):.1f}" y="{H-B+28}" font-size="9.5" fill="{MUTED}" text-anchor="middle">{b}</text>'
                 f'<text x="{X(i):.1f}" y="{Y(v)-10:.1f}" font-size="11" font-weight="800" fill="{BRAND}" text-anchor="middle">{v}</text>')
    o.append("</svg>")
    return "".join(o)


def main(name):
    src = (HERE / f"{name}.src.html").read_text(encoding="utf-8")
    src = src.replace("/*@@THEME@@*/", re.sub(r"\{\{FONT:([^}]+)\}\}", font, THEME_CSS))
    src = re.sub(r"\{\{IMG:([^}]+)\}\}", img, src)
    cp = HERE / "charts.py"
    if cp.exists():
        spec = importlib.util.spec_from_file_location("charts", cp); m = importlib.util.module_from_spec(spec); m.THEME = THEME; spec.loader.exec_module(m)
        for k, fn in m.CHARTS.items():
            src = src.replace("{{CHART:%s}}" % k, fn())
    out = HERE / f"{name}.html"
    out.write_text(src, encoding="utf-8")
    print(out, f"{out.stat().st_size/1024:.0f} KiB", file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "artikel")
