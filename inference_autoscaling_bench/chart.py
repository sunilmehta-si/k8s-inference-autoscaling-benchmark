"""One SVG of the first run: the demand, the pods each policy kept, and the queue it let build."""
from __future__ import annotations

W, H = 760, 560
LEFT, RIGHT, TOP = 56, 16, 52
PANEL_H, GAP = 128, 34
PALETTE = ["#0072b2", "#d55e00", "#009e73", "#cc79a7", "#e69f00", "#56b4e9", "#7a5c00", "#44aa99"]
QUEUE_CLIP = 1000


def _scale(value: float, top: float, y0: float, height: float) -> float:
    return y0 + height - min(value, top) / top * height


def _nice(value: float) -> float:
    for step in (1, 2, 5, 10, 20, 25, 50, 100, 200, 250, 500, 1000):
        if value <= step:
            return step
    return value


def svg(doc: dict) -> str:
    duration = doc["workload"]["duration_s"]
    width = W - LEFT - RIGHT
    x = lambda t: LEFT + t / duration * width  # noqa: E731
    labels = [p["label"] for p in doc["policies"]]
    colour = {label: PALETTE[i % len(PALETTE)] for i, label in enumerate(labels)}
    timelines = doc["timelines"]
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" '
        f'aria-label="Demand, pods and queue over the first run of {doc["workload"]["name"]}">',
        "<style>:root{--fg:#24292f;--grid:#d0d7de;--bg:#fff}@media (prefers-color-scheme:dark){:root{--fg:#e6edf3;--grid:#30363d;--bg:#0d1117}}"
        "text{fill:var(--fg);font:12px system-ui,sans-serif}.grid{stroke:var(--grid);stroke-width:1}.t{font-weight:600}</style>",
        f'<rect width="{W}" height="{H}" fill="var(--bg)"/>',
    ]
    lx = LEFT
    for label in labels:
        dash = ' stroke-dasharray="5 3"' if label.startswith("static-") else ""
        out.append(f'<line x1="{lx}" y1="16" x2="{lx + 18}" y2="16" stroke="{colour[label]}" stroke-width="3"{dash}/>')
        out.append(f'<text x="{lx + 22}" y="20">{label}</text>')
        lx += 30 + 7 * len(label)
        if lx > W - 120:
            break

    def panel(index: int, title: str, top: float, unit: str):
        y0 = TOP + index * (PANEL_H + GAP)
        out.append(f'<text class="t" x="{LEFT}" y="{y0 - 8}">{title}</text>')
        for fraction in (0, 0.5, 1):
            y = y0 + PANEL_H - fraction * PANEL_H
            out.append(f'<line class="grid" x1="{LEFT}" y1="{y:.1f}" x2="{W - RIGHT}" y2="{y:.1f}"/>')
            out.append(f'<text x="{LEFT - 6}" y="{y + 4:.1f}" text-anchor="end">{top * fraction:g}{unit if fraction == 1 else ""}</text>')
        return y0

    demand = doc["demand"]
    top = _nice(max(rate for _, rate in demand))
    y0 = panel(0, "Requests per second arriving", top, "")
    points = [f"{x(0):.1f},{y0 + PANEL_H:.1f}"] + [f"{x(t):.1f},{_scale(rate, top, y0, PANEL_H):.1f}" for t, rate in demand]
    points.append(f"{x(demand[-1][0]):.1f},{y0 + PANEL_H:.1f}")
    out.append(f'<polygon points="{" ".join(points)}" fill="#8c959f" fill-opacity="0.45"/>')

    top = _nice(max(row[1] + row[2] for tl in timelines.values() for row in tl))
    y0 = panel(1, "Pods that exist (ready and starting)", top, "")
    for label in labels:
        pts = " ".join(f"{x(row[0]):.1f},{_scale(row[1] + row[2], top, y0, PANEL_H):.1f}" for row in timelines[label])
        dash = ' stroke-dasharray="5 3"' if label.startswith("static-") else ""
        out.append(f'<polyline points="{pts}" fill="none" stroke="{colour[label]}" stroke-width="2"{dash}/>')

    y0 = panel(2, f"Requests waiting (clipped at {QUEUE_CLIP:,})", QUEUE_CLIP, "")
    for label in labels:
        pts = " ".join(f"{x(row[0]):.1f},{_scale(row[4], QUEUE_CLIP, y0, PANEL_H):.1f}" for row in timelines[label])
        dash = ' stroke-dasharray="5 3"' if label.startswith("static-") else ""
        out.append(f'<polyline points="{pts}" fill="none" stroke="{colour[label]}" stroke-width="2"{dash}/>')
    for minute in range(0, int(duration // 60) + 1, 5):
        out.append(f'<text x="{x(minute * 60):.1f}" y="{TOP + 3 * PANEL_H + 2 * GAP + 16}" text-anchor="middle">{minute} min</text>')
    out.append("</svg>")
    return "\n".join(out) + "\n"
