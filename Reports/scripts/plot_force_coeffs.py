#!/usr/bin/env python3
"""Plot Cd and Cl vs iteration for ahmed-bluff-body-OF-2406 (case 1-A).

Reads postProcessing/forceCoeffs1/*/coefficient.dat and writes:
  Reports/data/Cd_vs_iteration.csv
  Reports/data/Cl_vs_iteration.csv
  Reports/figures/Cd_vs_iteration.svg
  Reports/figures/Cl_vs_iteration.svg

Usage (from case root or anywhere):
  python3 Reports/scripts/plot_force_coeffs.py
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path

CASE = Path(__file__).resolve().parents[2]  # ahmed-bluff-body-OF-2406/
OUT_DATA = CASE / "Reports" / "data"
OUT_FIG = CASE / "Reports" / "figures"

# Experimental targets (25° Ahmed), TU Graz / case 1-A README
REF_CD = 0.299
REF_CL = 0.345

COLOR_CD = "#c45c26"
COLOR_CL = "#2f6fed"


def find_coefficient_dat() -> Path | None:
    preferred = CASE / "postProcessing" / "forceCoeffs1" / "0" / "coefficient.dat"
    if preferred.exists():
        return preferred
    matches = sorted((CASE / "postProcessing").glob("**/coefficient.dat"))
    return matches[0] if matches else None


def load_cd_cl(path: Path) -> list[tuple[float, float, float]]:
    """Return (Time/iteration, Cd, Cl)."""
    rows: list[tuple[float, float, float]] = []
    for line in path.read_text().splitlines():
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 5:
            continue
        rows.append((float(parts[0]), float(parts[1]), float(parts[4])))
    return rows


def nice_ticks(a: float, b: float, n: int = 5) -> list[float]:
    span = b - a
    if span <= 0:
        return [a]
    step = 10 ** math.floor(math.log10(span / max(n, 1)))
    for m in (1, 2, 5, 10):
        if span / (m * step) <= n + 1:
            step = m * step
            break
    start = math.ceil(a / step - 1e-12) * step
    ticks: list[float] = []
    v = start
    while v <= b + 1e-9 * max(1.0, abs(b)):
        ticks.append(v)
        v += step
        if len(ticks) > 20:
            break
    return ticks or [a, b]


def svg_plot(
    pts: list[tuple[float, float]],
    path: Path,
    *,
    title: str,
    ylabel: str,
    color: str,
    ref: float,
    ref_label: str,
    series_name: str,
    y_min: float | None = None,
    y_max: float | None = None,
    width: int = 720,
    height: int = 420,
) -> None:
    if not pts:
        return

    t0, t1 = pts[0][0], pts[-1][0]
    vals = [c for _, c in pts]
    c0, c1 = min(vals), max(vals)
    pad = max(0.02, 0.08 * (c1 - c0 or 0.1))
    c0, c1 = c0 - pad, c1 + pad
    # Keep ref line in view
    c0 = min(c0, ref - pad)
    c1 = max(c1, ref + pad)
    if y_min is not None:
        c0 = y_min
    if y_max is not None:
        c1 = y_max
    if t1 == t0:
        t1 = t0 + 1e-6

    ml, mr, mt, mb = 64, 24, 40, 52
    pw, ph = width - ml - mr, height - mt - mb

    def x(t: float) -> float:
        return ml + (t - t0) / (t1 - t0) * pw

    def y(c: float) -> float:
        c_clamped = min(max(c, c0), c1)
        return mt + (1 - (c_clamped - c0) / (c1 - c0)) * ph

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<text x="{width/2}" y="24" text-anchor="middle" '
        f'font-family="Helvetica,Arial,sans-serif" font-size="14" fill="#111">{title}</text>',
        f'<line x1="{ml}" y1="{mt}" x2="{ml}" y2="{mt+ph}" stroke="#333" stroke-width="1"/>',
        f'<line x1="{ml}" y1="{mt+ph}" x2="{ml+pw}" y2="{mt+ph}" stroke="#333" stroke-width="1"/>',
        f'<text x="{ml-10}" y="{mt-8}" text-anchor="end" '
        f'font-family="Helvetica,Arial,sans-serif" font-size="11" fill="#444">{ylabel}</text>',
        f'<text x="{ml+pw/2}" y="{height-10}" text-anchor="middle" '
        f'font-family="Helvetica,Arial,sans-serif" font-size="11" fill="#444">Iteration</text>',
    ]

    for tv in nice_ticks(t0, t1, 6):
        xx = x(tv)
        parts.append(
            f'<line x1="{xx}" y1="{mt}" x2="{xx}" y2="{mt+ph}" stroke="#e8e8e8" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{xx}" y="{mt+ph+16}" text-anchor="middle" '
            f'font-family="Helvetica,Arial,sans-serif" font-size="10" fill="#555">'
            f"{tv:.0f}</text>"
        )

    for cv in nice_ticks(c0, c1, 5):
        yy = y(cv)
        parts.append(
            f'<line x1="{ml}" y1="{yy}" x2="{ml+pw}" y2="{yy}" stroke="#e8e8e8" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{ml-8}" y="{yy+3}" text-anchor="end" '
            f'font-family="Helvetica,Arial,sans-serif" font-size="10" fill="#555">'
            f"{cv:.2f}</text>"
        )

    if c0 <= ref <= c1:
        yy = y(ref)
        parts.append(
            f'<line x1="{ml}" y1="{yy}" x2="{ml+pw}" y2="{yy}" '
            f'stroke="#888" stroke-width="1" stroke-dasharray="4 3"/>'
        )
        parts.append(
            f'<text x="{ml+pw-4}" y="{yy-4}" text-anchor="end" '
            f'font-family="Helvetica,Arial,sans-serif" font-size="10" fill="#666">'
            f"{ref_label}={ref:.3f}</text>"
        )

    step = max(1, len(pts) // 800)
    pts_d = pts[::step]
    if pts_d[-1] != pts[-1]:
        pts_d = pts_d + [pts[-1]]
    d = " ".join(
        f"{'M' if j == 0 else 'L'}{x(t):.2f},{y(c):.2f}"
        for j, (t, c) in enumerate(pts_d)
    )
    parts.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="1.6"/>')

    t_last, c_last = pts[-1]
    ly = mt + 8
    parts.append(
        f'<line x1="{ml+10}" y1="{ly}" x2="{ml+28}" y2="{ly}" '
        f'stroke="{color}" stroke-width="2"/>'
    )
    parts.append(
        f'<text x="{ml+34}" y="{ly+3}" font-family="Helvetica,Arial,sans-serif" '
        f'font-size="11" fill="#222">'
        f"{series_name} ({ylabel}={c_last:.3f} @ {t_last:.0f})</text>"
    )

    parts.append("</svg>")
    path.write_text("\n".join(parts) + "\n")


def mean_last_n(rows: list[tuple[float, float]], n: int = 50) -> float:
    tail = rows[-min(n, len(rows)) :]
    return sum(c for _, c in tail) / len(tail)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ref-cd", type=float, default=REF_CD)
    ap.add_argument("--ref-cl", type=float, default=REF_CL)
    ap.add_argument("--y-max-cd", type=float, default=0.80,
                    help="Cd axis upper limit (clips early transients visually).")
    ap.add_argument("--y-min-cd", type=float, default=0.0)
    ap.add_argument("--y-max-cl", type=float, default=0.60)
    ap.add_argument("--y-min-cl", type=float, default=0.0)
    args = ap.parse_args()

    coeff = find_coefficient_dat()
    if not coeff:
        raise SystemExit(f"No coefficient.dat under {CASE / 'postProcessing'}")

    rows = load_cd_cl(coeff)
    if not rows:
        raise SystemExit(f"No data rows in {coeff}")

    OUT_DATA.mkdir(parents=True, exist_ok=True)
    OUT_FIG.mkdir(parents=True, exist_ok=True)

    cd_pts = [(t, cd) for t, cd, _ in rows]
    cl_pts = [(t, cl) for t, _, cl in rows]

    with open(OUT_DATA / "Cd_vs_iteration.csv", "w") as f:
        f.write("iteration,Cd\n")
        for t, cd in cd_pts:
            f.write(f"{t:.0f},{cd:.8e}\n")

    with open(OUT_DATA / "Cl_vs_iteration.csv", "w") as f:
        f.write("iteration,Cl\n")
        for t, cl in cl_pts:
            f.write(f"{t:.0f},{cl:.8e}\n")

    svg_plot(
        cd_pts,
        OUT_FIG / "Cd_vs_iteration.svg",
        title="Cd vs iteration — Ahmed 25° (case 1-A)",
        ylabel="Cd",
        color=COLOR_CD,
        ref=args.ref_cd,
        ref_label="exp Cd",
        series_name="simpleFoam kOmegaSST",
        y_min=args.y_min_cd,
        y_max=args.y_max_cd,
    )
    svg_plot(
        cl_pts,
        OUT_FIG / "Cl_vs_iteration.svg",
        title="Cl vs iteration — Ahmed 25° (case 1-A)",
        ylabel="Cl",
        color=COLOR_CL,
        ref=args.ref_cl,
        ref_label="exp Cl",
        series_name="simpleFoam kOmegaSST",
        y_min=args.y_min_cl,
        y_max=args.y_max_cl,
    )

    cd_mean50 = mean_last_n(cd_pts, 50)
    cl_mean50 = mean_last_n(cl_pts, 50)
    print(f"source: {coeff.relative_to(CASE)}")
    print(f"n={len(rows)}  iter={rows[0][0]:.0f}..{rows[-1][0]:.0f}")
    print(f"Cd last={cd_pts[-1][1]:.4f}  mean(last50)={cd_mean50:.4f}  exp={args.ref_cd}")
    print(f"Cl last={cl_pts[-1][1]:.4f}  mean(last50)={cl_mean50:.4f}  exp={args.ref_cl}")
    print(f"figures → {OUT_FIG}")


if __name__ == "__main__":
    main()
