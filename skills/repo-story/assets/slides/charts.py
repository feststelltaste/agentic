"""Example charts (menu width, fidelity) for the slide templates. Colors come from the theme (THEME is set by build.py).
Own charts: write functions without arguments that return an <svg> and register them in CHARTS; line_chart() in build.py helps.
The `_de` chart functions keep their German axis labels on purpose (for the German example slides)."""
import datetime as dt
BRAND, BRAND25, MUTED, LINE, ACCENT, ACCENT_INK = (THEME[k] for k in ("brand", "brand-25", "muted", "line", "accent", "accent-ink"))


def parity_svg():
    pts = [("2026-10-01 08:25", 518), ("2026-10-01 09:16", 532), ("2026-10-01 22:49", 600), ("2026-10-02 16:43", 605),
           ("2026-10-02 20:40", 606), ("2026-10-03 00:37", 607), ("2026-10-03 00:44", 608), ("2026-10-03 02:23", 609),
           ("2026-10-03 02:43", 618), ("2026-10-03 02:50", 624), ("2026-10-03 02:56", 625)]
    t0, t1 = dt.datetime(2026, 10, 1, 6), dt.datetime(2026, 10, 3, 6)
    W, H, L, R, T, B = 660, 230, 44, 92, 18, 34
    y0, y1 = 500, 630
    X = lambda t: L + (t - t0).total_seconds() / (t1 - t0).total_seconds() * (W - L - R)
    Y = lambda v: T + (y1 - v) / (y1 - y0) * (H - T - B)
    P = [(X(dt.datetime.fromisoformat(s)), Y(v), v) for s, v in pts]
    o = [f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" aria-label="Menu breadth: 518 to 625 of 625 menu items between 1 and 3 October">']
    for v in (520, 560, 600):
        o.append(f'<line x1="{L}" x2="{W-R}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" stroke="{LINE}" stroke-width="1"/>'
                 f'<text x="{L-8}" y="{Y(v)+3.5:.1f}" font-size="10" fill="{MUTED}" text-anchor="end">{v}</text>')
    o.append(f'<line x1="{L}" x2="{W-R}" y1="{Y(625):.1f}" y2="{Y(625):.1f}" stroke="{BRAND25}" stroke-width="1" stroke-dasharray="3 3"/>'
             f'<text x="{W-R+8}" y="{Y(625)+3.5:.1f}" font-size="10" fill="{MUTED}">all 625</text>')
    for lab, t in (("1 Oct, 12:00", dt.datetime(2026, 10, 1, 12)), ("2 Oct, 00:00", dt.datetime(2026, 10, 2)),
                   ("2 Oct, 12:00", dt.datetime(2026, 10, 2, 12)), ("3 Oct, 00:00", dt.datetime(2026, 10, 3))):
        o.append(f'<line x1="{X(t):.1f}" x2="{X(t):.1f}" y1="{H-B}" y2="{H-B+4}" stroke="{MUTED}"/>'
                 f'<text x="{X(t):.1f}" y="{H-B+17}" font-size="10" fill="{MUTED}" text-anchor="middle">{lab}</text>')
    o.append(f'<line x1="{L}" x2="{W-R}" y1="{H-B}" y2="{H-B}" stroke="{MUTED}" stroke-width="1"/>')
    # sprint marker: the last 33 minutes
    xa, xb = P[7][0], P[-1][0]
    o.append(f'<rect x="{xa-3:.1f}" y="{T}" width="{xb-xa+6:.1f}" height="{H-T-B}" fill="{ACCENT}" opacity=".18"/>')
    d = f"M{P[0][0]:.1f},{P[0][1]:.1f}"
    for (x, y, _), (nx, ny, _) in zip(P, P[1:]):
        d += f" H{nx:.1f} V{ny:.1f}"
    o.append(f'<path d="{d}" fill="none" stroke="{BRAND}" stroke-width="2" stroke-linejoin="round"/>')
    for x, y, v in (P[0], P[-1]):
        o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="{BRAND}" stroke="#fff" stroke-width="2"/>')
    o.append(f'<text x="{P[0][0]+7:.1f}" y="{P[0][1]+15:.1f}" font-size="11" font-weight="800" fill="{BRAND}">518</text>')
    o.append(f'<text x="{P[0][0]+7:.1f}" y="{P[0][1]+28:.1f}" font-size="9.5" fill="{MUTED}">first count, 1 Oct 08:25</text>')
    o.append(f'<text x="{P[-1][0]+8:.1f}" y="{P[-1][1]-8:.1f}" font-size="11" font-weight="800" fill="{BRAND}">625</text>')
    o.append(f'<text x="{xa-8:.1f}" y="{Y(560):.1f}" font-size="9.5" fill="{ACCENT_INK}" text-anchor="end">609 → 625</text>'
             f'<text x="{xa-8:.1f}" y="{Y(560)+13:.1f}" font-size="9.5" fill="{ACCENT_INK}" text-anchor="end">in 33 minutes</text>')
    o.append("</svg>")
    return "".join(o)


def fidelity_svg():
    pts = [("0.1.1", "3 Oct", 70), ("0.2.0", "5 Oct", 72), ("Nr. 192", "before", 74), ("Nr. 193", "text gamma", 128),
           ("0.3.0", "7 Oct", 130), ("HEAD", "8 Oct", 133)]
    W, H, L, R, T, B = 660, 230, 44, 92, 18, 40
    Y = lambda v: T + (270 - v) / 270 * (H - T - B)
    step = (W - L - R - 40) / (len(pts) - 1)
    X = lambda i: L + 20 + i * step
    o = [f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" aria-label="Fidelity: 70, 72, 74, 128, 130, 133 of 258 files">']
    for v in (0, 100, 200):
        o.append(f'<line x1="{L}" x2="{W-R}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" stroke="{MUTED if v == 0 else LINE}" stroke-width="1"/>'
                 f'<text x="{L-8}" y="{Y(v)+3.5:.1f}" font-size="10" fill="{MUTED}" text-anchor="end">{v}</text>')
    o.append(f'<line x1="{L}" x2="{W-R}" y1="{Y(258):.1f}" y2="{Y(258):.1f}" stroke="{BRAND25}" stroke-width="1" stroke-dasharray="3 3"/>'
             f'<text x="{W-R+8}" y="{Y(258)+3.5:.1f}" font-size="10" fill="{MUTED}">all 258</text>')
    o.append(f'<rect x="{X(2)+6:.1f}" y="{T}" width="{step-12:.1f}" height="{H-T-B}" fill="{ACCENT}" opacity=".18"/>')
    o.append(f'<text x="{(X(2)+X(3))/2:.1f}" y="{Y(200)+4:.1f}" font-size="9.5" fill="{ACCENT_INK}" text-anchor="middle">one commit</text>'
             f'<text x="{(X(2)+X(3))/2:.1f}" y="{Y(200)+17:.1f}" font-size="9.5" fill="{ACCENT_INK}" text-anchor="middle">+54</text>')
    d = " ".join(f"{'M' if i == 0 else 'L'}{X(i):.1f},{Y(v):.1f}" for i, (_, _, v) in enumerate(pts))
    o.append(f'<path d="{d}" fill="none" stroke="{BRAND}" stroke-width="2" stroke-linejoin="round"/>')
    for i, (a, b, v) in enumerate(pts):
        o.append(f'<circle cx="{X(i):.1f}" cy="{Y(v):.1f}" r="4" fill="{BRAND}" stroke="#fff" stroke-width="2"/>')
        o.append(f'<text x="{X(i):.1f}" y="{H-B+15}" font-size="10" font-weight="800" fill="{BRAND}" text-anchor="middle">{a}</text>'
                 f'<text x="{X(i):.1f}" y="{H-B+28}" font-size="9.5" fill="{MUTED}" text-anchor="middle">{b}</text>')
        if i in (0, 2, 3, 5):
            o.append(f'<text x="{X(i):.1f}" y="{Y(v)-10:.1f}" font-size="11" font-weight="800" fill="{BRAND}" text-anchor="middle">{v}</text>')
    o.append("</svg>")
    return "".join(o)



def parity_svg_de():
    pts = [("2026-10-01 08:25", 518), ("2026-10-01 09:16", 532), ("2026-10-01 22:49", 600), ("2026-10-02 16:43", 605),
           ("2026-10-02 20:40", 606), ("2026-10-03 00:37", 607), ("2026-10-03 00:44", 608), ("2026-10-03 02:23", 609),
           ("2026-10-03 02:43", 618), ("2026-10-03 02:50", 624), ("2026-10-03 02:56", 625)]
    t0, t1 = dt.datetime(2026, 10, 1, 6), dt.datetime(2026, 10, 3, 6)
    W, H, L, R, T, B = 660, 230, 44, 92, 18, 34
    y0, y1 = 500, 630
    X = lambda t: L + (t - t0).total_seconds() / (t1 - t0).total_seconds() * (W - L - R)
    Y = lambda v: T + (y1 - v) / (y1 - y0) * (H - T - B)
    P = [(X(dt.datetime.fromisoformat(s)), Y(v), v) for s, v in pts]
    o = [f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" aria-label="Menübreite: 518 bis 625 von 625 Menüpunkten zwischen 1. und 3. Oktober">']
    for v in (520, 560, 600):
        o.append(f'<line x1="{L}" x2="{W-R}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" stroke="{LINE}" stroke-width="1"/>'
                 f'<text x="{L-8}" y="{Y(v)+3.5:.1f}" font-size="10" fill="{MUTED}" text-anchor="end">{v}</text>')
    o.append(f'<line x1="{L}" x2="{W-R}" y1="{Y(625):.1f}" y2="{Y(625):.1f}" stroke="{BRAND25}" stroke-width="1" stroke-dasharray="3 3"/>'
             f'<text x="{W-R+8}" y="{Y(625)+3.5:.1f}" font-size="10" fill="{MUTED}">alle 625</text>')
    for lab, t in (("1. Okt, 12 Uhr", dt.datetime(2026, 10, 1, 12)), ("2. Okt, 0 Uhr", dt.datetime(2026, 10, 2)),
                   ("2. Okt, 12 Uhr", dt.datetime(2026, 10, 2, 12)), ("3. Okt, 0 Uhr", dt.datetime(2026, 10, 3))):
        o.append(f'<line x1="{X(t):.1f}" x2="{X(t):.1f}" y1="{H-B}" y2="{H-B+4}" stroke="{MUTED}"/>'
                 f'<text x="{X(t):.1f}" y="{H-B+17}" font-size="10" fill="{MUTED}" text-anchor="middle">{lab}</text>')
    o.append(f'<line x1="{L}" x2="{W-R}" y1="{H-B}" y2="{H-B}" stroke="{MUTED}" stroke-width="1"/>')
    # sprint marker: the last 33 minutes
    xa, xb = P[7][0], P[-1][0]
    o.append(f'<rect x="{xa-3:.1f}" y="{T}" width="{xb-xa+6:.1f}" height="{H-T-B}" fill="{ACCENT}" opacity=".18"/>')
    d = f"M{P[0][0]:.1f},{P[0][1]:.1f}"
    for (x, y, _), (nx, ny, _) in zip(P, P[1:]):
        d += f" H{nx:.1f} V{ny:.1f}"
    o.append(f'<path d="{d}" fill="none" stroke="{BRAND}" stroke-width="2" stroke-linejoin="round"/>')
    for x, y, v in (P[0], P[-1]):
        o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="{BRAND}" stroke="#fff" stroke-width="2"/>')
    o.append(f'<text x="{P[0][0]+7:.1f}" y="{P[0][1]+15:.1f}" font-size="11" font-weight="800" fill="{BRAND}">518</text>')
    o.append(f'<text x="{P[0][0]+7:.1f}" y="{P[0][1]+28:.1f}" font-size="9.5" fill="{MUTED}">erste Zählung, 1. Okt 08:25</text>')
    o.append(f'<text x="{P[-1][0]+8:.1f}" y="{P[-1][1]-8:.1f}" font-size="11" font-weight="800" fill="{BRAND}">625</text>')
    o.append(f'<text x="{xa-8:.1f}" y="{Y(560):.1f}" font-size="9.5" fill="{ACCENT_INK}" text-anchor="end">609 → 625</text>'
             f'<text x="{xa-8:.1f}" y="{Y(560)+13:.1f}" font-size="9.5" fill="{ACCENT_INK}" text-anchor="end">in 33 Minuten</text>')
    o.append("</svg>")
    return "".join(o)


def fidelity_svg_de():
    pts = [("0.1.1", "3. Okt", 70), ("0.2.0", "5. Okt", 72), ("Nr. 192", "vorher", 74), ("Nr. 193", "Text-Gamma", 128),
           ("0.3.0", "7. Okt", 130), ("HEAD", "8. Okt", 133)]
    W, H, L, R, T, B = 660, 230, 44, 92, 18, 40
    Y = lambda v: T + (270 - v) / 270 * (H - T - B)
    step = (W - L - R - 40) / (len(pts) - 1)
    X = lambda i: L + 20 + i * step
    o = [f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" aria-label="Treue: 70, 72, 74, 128, 130, 133 von 258 Dateien">']
    for v in (0, 100, 200):
        o.append(f'<line x1="{L}" x2="{W-R}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" stroke="{MUTED if v == 0 else LINE}" stroke-width="1"/>'
                 f'<text x="{L-8}" y="{Y(v)+3.5:.1f}" font-size="10" fill="{MUTED}" text-anchor="end">{v}</text>')
    o.append(f'<line x1="{L}" x2="{W-R}" y1="{Y(258):.1f}" y2="{Y(258):.1f}" stroke="{BRAND25}" stroke-width="1" stroke-dasharray="3 3"/>'
             f'<text x="{W-R+8}" y="{Y(258)+3.5:.1f}" font-size="10" fill="{MUTED}">alle 258</text>')
    o.append(f'<rect x="{X(2)+6:.1f}" y="{T}" width="{step-12:.1f}" height="{H-T-B}" fill="{ACCENT}" opacity=".18"/>')
    o.append(f'<text x="{(X(2)+X(3))/2:.1f}" y="{Y(200)+4:.1f}" font-size="9.5" fill="{ACCENT_INK}" text-anchor="middle">ein Commit</text>'
             f'<text x="{(X(2)+X(3))/2:.1f}" y="{Y(200)+17:.1f}" font-size="9.5" fill="{ACCENT_INK}" text-anchor="middle">+54</text>')
    d = " ".join(f"{'M' if i == 0 else 'L'}{X(i):.1f},{Y(v):.1f}" for i, (_, _, v) in enumerate(pts))
    o.append(f'<path d="{d}" fill="none" stroke="{BRAND}" stroke-width="2" stroke-linejoin="round"/>')
    for i, (a, b, v) in enumerate(pts):
        o.append(f'<circle cx="{X(i):.1f}" cy="{Y(v):.1f}" r="4" fill="{BRAND}" stroke="#fff" stroke-width="2"/>')
        o.append(f'<text x="{X(i):.1f}" y="{H-B+15}" font-size="10" font-weight="800" fill="{BRAND}" text-anchor="middle">{a}</text>'
                 f'<text x="{X(i):.1f}" y="{H-B+28}" font-size="9.5" fill="{MUTED}" text-anchor="middle">{b}</text>')
        if i in (0, 2, 3, 5):
            o.append(f'<text x="{X(i):.1f}" y="{Y(v)-10:.1f}" font-size="11" font-weight="800" fill="{BRAND}" text-anchor="middle">{v}</text>')
    o.append("</svg>")
    return "".join(o)



CHARTS = {"parity": parity_svg, "fidelity": fidelity_svg, "parity-de": parity_svg_de, "fidelity-de": fidelity_svg_de}
