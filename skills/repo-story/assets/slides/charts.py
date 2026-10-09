"""Example charts for the slide templates (sample data: replace it with your measurements).
Colors come from the theme (THEME is set by build.py). line_chart() from build.py is available here as well.
Own charts: write functions without arguments that return an <svg> and register them in CHARTS, then use {{CHART:name}} in the slide.
The `-de` variants only differ in their labels (for the German templates)."""


def chart_1(de=False):
    pts = [("A", "Tag 1" if de else "day 1", 12), ("B", "Tag 2" if de else "day 2", 30),
           ("C", "Tag 3" if de else "day 3", 31), ("D", "Tag 4" if de else "day 4", 66)]
    return line_chart(pts, 0, 90, ref=90, ref_label="Ziel 90" if de else "goal 90", step=True,
                      label="Beispiel: Wert über die Zeit" if de else "Example: value over time")


def chart_2(de=False):
    pts = [("r1", "alt" if de else "old", 40), ("r2", "", 55), ("r3", "", 58), ("r4", "neu" if de else "new", 96)]
    return line_chart(pts, 0, 120, ref=100, ref_label="alle 100" if de else "all 100",
                      label="Beispiel: Treffer je Stand" if de else "Example: hits per revision")


CHARTS = {"chart-1": chart_1, "chart-2": chart_2,
          "chart-1-de": lambda: chart_1(True), "chart-2-de": lambda: chart_2(True)}
