#!/usr/bin/env python3
"""
neon-contrib — Generates an animated SVG contribution grid
for GitHub profile READMEs. Replaces the snake animation.

Place in repo root. Run via neon.yml.
Env vars:
  GITHUB_TOKEN  — provided automatically by Actions
  GH_USER       — GitHub username  (default: akamohid)
  OUTPUT_PATH   — output path      (default: dist/neon-contributions.svg)
"""

import os, sys, requests
from datetime import datetime

# ── config ───────────────────────────────────────────────────────────────────
USERNAME = os.environ.get("GH_USER", "akamohid")
TOKEN    = os.environ.get("GITHUB_TOKEN", "")
OUT      = os.environ.get("OUTPUT_PATH", "dist/neon-contributions.svg")

# Contribution level → base fill color  (0 = empty … 4 = max commits)
FILL = ["#0d001f", "#2d0055", "#A259FF", "#FF2D78", "#00E5FF"]
# Color at animation peak (lighter / brighter)
GLOW = ["#180030", "#4a1a80", "#BF7FFF", "#FF6BA0", "#60F4FF"]
# Gaussian blur radius per level (drives the glow halo)
BLUR = [0, 1.2, 2.0, 2.8, 3.5]

CELL = 11; GAP = 2; STEP = CELL + GAP
PX   = 24; PY = 18; FOOT = 22

QUERY = """
query($u: String!) {
  user(login: $u) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays { contributionCount  weekday }
        }
      }
    }
  }
}"""

# ── helpers ──────────────────────────────────────────────────────────────────

def level(n: int) -> int:
    if n == 0:  return 0
    if n <= 3:  return 1
    if n <= 6:  return 2
    if n <= 12: return 3
    return 4

def fetch() -> dict:
    r = requests.post(
        "https://api.github.com/graphql",
        json={"query": QUERY, "variables": {"u": USERNAME}},
        headers={"Authorization": f"Bearer {TOKEN}"},
        timeout=20,
    )
    r.raise_for_status()
    body = r.json()
    if "errors" in body:
        raise RuntimeError(body["errors"])
    return body["data"]["user"]["contributionsCollection"]["contributionCalendar"]

# ── SVG builder ──────────────────────────────────────────────────────────────

def build_svg(cal: dict) -> str:
    weeks = cal["weeks"]
    total = cal["totalContributions"]
    W     = len(weeks)

    svgW = W * STEP + PX * 2
    svgH = 7 * STEP + PY + FOOT

    # ── cells ─────────────────────────────────────────────────────────────────
    cell_parts = []
    for wi, week in enumerate(weeks):
        for day in week["contributionDays"]:
            v  = level(day["contributionCount"])
            x  = wi * STEP + PX
            y  = day["weekday"] * STEP + PY
            flt = f' filter="url(#g{v})"' if v else ""
            cell_parts.append(
                f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" '
                f'rx="2" fill="{FILL[v]}" class="c{v}"{flt}/>'
            )
    cells_html = "\n  ".join(cell_parts)

    # ── CSS pulse animations (one keyframe per level) ──────────────────────────
    css_lines = []
    for v in range(5):
        css_lines.append(f".c{v} {{ animation: p{v} 6s ease-in-out infinite; }}")
    for v in range(5):
        op_lo = 0.30 if v == 0 else 0.65
        op_hi = 0.50 if v == 0 else 1.00
        css_lines.append(
            f"@keyframes p{v} {{\n"
            f"  0%, 100% {{ opacity: {op_lo}; fill: {FILL[v]}; }}\n"
            f"  50%       {{ opacity: {op_hi}; fill: {GLOW[v]}; }}\n"
            f"}}"
        )
    css_block = "\n".join(css_lines)

    # ── glow blur filters ─────────────────────────────────────────────────────
    filter_parts = []
    for v in range(1, 5):
        filter_parts.append(
            f'<filter id="g{v}" x="-80%" y="-80%" width="260%" height="260%">'
            f'<feGaussianBlur in="SourceGraphic" stdDeviation="{BLUR[v]}" result="b"/>'
            f'<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>'
            f'</filter>'
        )
    filters_html = "\n  ".join(filter_parts)

    # ── scan-line metrics ─────────────────────────────────────────────────────
    scan_y    = PY - 5
    scan_h    = 7 * STEP + 10
    x_from    = -70
    x_to      = svgW + 30
    sweep_end = "0.55"
    fade_end  = f"{float(sweep_end) + 0.04:.2f}"
    year      = datetime.now().year

    return f"""<svg xmlns="http://www.w3.org/2000/svg"
  viewBox="0 0 {svgW} {svgH}" width="{svgW}" height="{svgH}">

<defs>
  <style>
{css_block}
  </style>

  {filters_html}

  <!-- scan-line gradient: purple → cyan → pink -->
  <linearGradient id="sg" x1="0%" x2="100%" y1="0%" y2="0%">
    <stop offset="0%"   stop-color="#A259FF" stop-opacity="0"/>
    <stop offset="25%"  stop-color="#A259FF" stop-opacity="0.85"/>
    <stop offset="50%"  stop-color="#00E5FF" stop-opacity="1"/>
    <stop offset="75%"  stop-color="#FF2D78" stop-opacity="0.85"/>
    <stop offset="100%" stop-color="#FF2D78" stop-opacity="0"/>
  </linearGradient>

  <!-- scan-line bloom -->
  <filter id="sf" x="-120%" y="-50%" width="340%" height="200%">
    <feGaussianBlur stdDeviation="5" result="b"/>
    <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
</defs>

<!-- Background -->
<rect width="{svgW}" height="{svgH}" fill="#06000f" rx="8"/>

<!-- Contribution cells -->
<g>
  {cells_html}
</g>

<!-- Neon scan line (SMIL — works inside img tags) -->
<rect x="{x_from}" y="{scan_y}" width="70" height="{scan_h}"
  rx="4" fill="url(#sg)" filter="url(#sf)">
  <animate attributeName="x"
    values="{x_from};{x_to};{x_to}"
    keyTimes="0;{sweep_end};1"
    dur="6s" repeatCount="indefinite"/>
  <animate attributeName="opacity"
    values="0;1;1;0;0"
    keyTimes="0;0.04;{sweep_end};{fade_end};1"
    dur="6s" repeatCount="indefinite"/>
</rect>

<!-- Footer -->
<text x="{PX}" y="{svgH - 6}"
  font-family="'Courier New',Courier,monospace" font-size="10"
  fill="#A259FF" opacity="0.8">{total} contributions · {year}</text>
<text x="{svgW - PX}" y="{svgH - 6}"
  font-family="'Courier New',Courier,monospace" font-size="10"
  fill="#00E5FF" opacity="0.8" text-anchor="end">github.com/{USERNAME}</text>

</svg>"""

# ── main ─────────────────────────────────────────────────────────────────────

def main():
    out_dir = os.path.dirname(OUT)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    print(f"▶  Fetching contributions for @{USERNAME} …")
    try:
        cal = fetch()
    except Exception as exc:
        print(f"✗  API error: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"   {cal['totalContributions']} contributions · {len(cal['weeks'])} weeks")
    print("▶  Building neon SVG …")
    svg = build_svg(cal)

    with open(OUT, "w", encoding="utf-8") as f:
        f.write(svg)

    print(f"✓  Saved → {OUT}  ({os.path.getsize(OUT)/1024:.1f} KB)")

if __name__ == "__main__":
    main()
