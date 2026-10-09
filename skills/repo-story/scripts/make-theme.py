#!/usr/bin/env python3
"""Creates a color theme from two colors: python3 make-theme.py <name> <brand> <accent> [--out folder] [--font "Family"]
Brand = dark main color (cover page, headings), accent = highlight (lines, markers). Everything else
(shades, text color, lines, readable accent ink with contrast >= 4.5:1) is derived.
Example: python3 make-theme.py mycompany "#12355b" "#ff7a59" --out ~/.config/repo-story/themes"""
import argparse, colorsys, pathlib, sys

def rgb(h): h = h.lstrip("#"); return tuple(int(h[i:i+2], 16) / 255 for i in (0, 2, 4))
def hexs(c): return "#" + "".join(f"{round(max(0, min(1, v)) * 255):02x}" for v in c)
def mix(a, b, t): return tuple(x * (1 - t) + y * t for x, y in zip(a, b))
def lum(c):
    f = lambda v: v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = map(f, c); return 0.2126 * r + 0.7152 * g + 0.0722 * b
def contrast(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True); return (la + 0.05) / (lb + 0.05)
def hsl(h, s, l): return colorsys.hls_to_rgb(h, l, s)

p = argparse.ArgumentParser(); p.add_argument("name"); p.add_argument("brand"); p.add_argument("accent")
p.add_argument("--out", default=str(pathlib.Path(__file__).resolve().parent.parent / "assets" / "themes"))
p.add_argument("--font", default=None, help="own font family instead of the bundled Source Sans 3")
a = p.parse_args()
W, K = (1, 1, 1), (0, 0, 0)
brand, accent = rgb(a.brand), rgb(a.accent)
hue = colorsys.rgb_to_hls(*brand)[0]
ink_acc = accent
while contrast(ink_acc, W) < 4.5:  # make the accent readable as text color on white
    ink_acc = mix(ink_acc, K, 0.06)
if contrast(brand, W) < 7: print("Note: brand color is light (contrast to white < 7:1), cover pages will look pale.", file=sys.stderr)
sans = (f'"{a.font}",' if a.font else '"Source Sans 3 Bundled",') + 'system-ui,-apple-system,"Segoe UI",Helvetica,Arial,sans-serif'
face = "" if a.font else '''@font-face{font-family:"Source Sans 3 Bundled";font-weight:400;font-style:normal;src:url({{FONT:SourceSans3-Regular.ttf}}) format("truetype");}
@font-face{font-family:"Source Sans 3 Bundled";font-weight:400;font-style:italic;src:url({{FONT:SourceSans3-Italic.ttf}}) format("truetype");}
@font-face{font-family:"Source Sans 3 Bundled";font-weight:700;font-style:normal;src:url({{FONT:SourceSans3-Bold.ttf}}) format("truetype");}
@font-face{font-family:"Source Sans 3 Bundled";font-weight:800;font-style:normal;src:url({{FONT:SourceSans3-ExtraBold.ttf}}) format("truetype");}
'''
css = f'''/* Theme "{a.name}": brand {a.brand}, accent {a.accent} (generated with scripts/make-theme.py) */
{face}:root{{
  --brand:{hexs(brand)}; --brand-75:{hexs(mix(brand, W, .25))}; --brand-25:{hexs(mix(brand, W, .75))}; --brand-soft:{hexs(mix(brand, W, .935))};
  --accent:{hexs(accent)}; --accent-ink:{hexs(ink_acc)}; --accent-soft:{hexs(mix(accent, W, .92))};
  --on-brand:{hexs(mix(brand, W, .87))};
  --ink:{hexs(hsl(hue, .28, .14))}; --muted:{hexs(hsl(hue, .12, .40))}; --line:{hexs(hsl(hue, .15, .89))};
  --faint:{hexs(hsl(hue, .08, .58))}; --screen-bg:{hexs(hsl(hue, .15, .93))};
  --sans:{sans};
  --mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
}}
'''
out = pathlib.Path(a.out).expanduser(); out.mkdir(parents=True, exist_ok=True)
(out / f"{a.name}.css").write_text(css, encoding="utf-8"); print(out / f"{a.name}.css")
