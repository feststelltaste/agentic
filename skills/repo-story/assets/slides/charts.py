"""Example charts for the slide templates (sample data: replace it with your measurements).
Colors come from the theme (THEME is set by build.py). line_chart() from build.py is available here as well.
Own charts: write functions without arguments that return an <svg> and register them in CHARTS, then use {{CHART:name}} in the slide.
"""


def chart_1():
    pts = [("A", "day 1", 12), ("B", "day 2", 30), ("C", "day 3", 31), ("D", "day 4", 66)]
    return line_chart(pts, 0, 90, ref=90, ref_label="goal 90", step=True, label="Example: value over time")


def chart_2():
    pts = [("r1", "old", 40), ("r2", "", 55), ("r3", "", 58), ("r4", "new", 96)]
    return line_chart(pts, 0, 120, ref=100, ref_label="all 100", label="Example: hits per revision")


CHARTS = {"chart-1": chart_1, "chart-2": chart_2}
