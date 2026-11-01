#!/usr/bin/env python3
"""
SPL contour maps around the Ahmed body from a compact Curle / dipole proxy.

Calibrated so the 1 m wake observer matches the demo OASPL (95.1 dB).
Useful for reporting before a full FW-H volume/surface reconstruction is available.

Usage:
  python3 scripts/caa/plot_spl_contour.py --out-dir Reports/caa/figures
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    from matplotlib.path import Path as MplPath
except ImportError as exc:  # pragma: no cover
    raise SystemExit("matplotlib required") from exc


PREF = 20e-6
L, H, W = 1.044, 0.288, 0.389
SRC = np.array([L + 0.05, 0.0, H * 0.45 + 0.05])
OBS = {
    "1 m wake": np.array([2.044, 0.0, 0.20]),
    "3 m wake": np.array([4.044, 0.0, 0.20]),
    "5 m wake": np.array([6.044, 0.0, 0.20]),
    "+1 m lat": np.array([2.044, 1.0, 0.20]),
    "-1 m lat": np.array([2.044, -1.0, 0.20]),
}
OASPL_1M = 95.1


def spl_field(X: np.ndarray, Y: np.ndarray, Z: np.ndarray) -> np.ndarray:
    p_rms_1m = PREF * 10 ** (OASPL_1M / 20)
    rx, ry, rz = X - SRC[0], Y - SRC[1], Z - SRC[2]
    r = np.maximum(np.sqrt(rx * rx + ry * ry + rz * rz), 0.08)
    diri = 0.75 * np.abs(rx / r) + 0.25 * (0.6 + 0.4 * np.abs(rz / r))
    r_ref = float(np.linalg.norm(OBS["1 m wake"] - SRC))
    dx = (OBS["1 m wake"][0] - SRC[0]) / r_ref
    dz = (OBS["1 m wake"][2] - SRC[2]) / r_ref
    diri_ref = 0.75 * abs(dx) + 0.25 * (0.6 + 0.4 * abs(dz))
    amp = p_rms_1m * r_ref / max(diri_ref, 1e-6)
    p_rms = np.maximum(amp * diri / r, PREF * 10 ** (35 / 20))
    return 20.0 * np.log10(p_rms / PREF)


def plot_symmetry(out: Path) -> Path:
    x = np.linspace(-0.5, 7.0, 400)
    z = np.linspace(0.0, 2.2, 220)
    X, Z = np.meshgrid(x, z)
    Y = np.zeros_like(X)
    SPL = spl_field(X, Y, Z)
    body_x = [0.0, 1.044, 1.044, 0.822, 0.0, 0.0]
    body_z = [0.05, 0.05, 0.10, 0.05 + 0.288, 0.05 + 0.288, 0.05]
    mask = MplPath(list(zip(body_x, body_z))).contains_points(
        np.column_stack([X.ravel(), Z.ravel()])
    ).reshape(X.shape)
    mask |= (X >= 0.0) & (X <= L) & (Z >= 0.0) & (Z <= 0.05)
    SPL_plot = np.ma.array(SPL, mask=mask)

    levels = np.linspace(55, 100, 19)
    cmap = plt.colormaps.get_cmap("magma")
    fig, ax = plt.subplots(figsize=(11, 4.2))
    cf = ax.contourf(X, Z, SPL_plot, levels=levels, cmap=cmap, extend="both")
    ax.contour(X, Z, SPL_plot, levels=levels[::2], colors="w", linewidths=0.35, alpha=0.45)
    ax.fill(body_x, body_z, color="#1a1a1a", zorder=5)
    ax.plot(body_x + [body_x[0]], body_z + [body_z[0]], color="w", lw=1.0, zorder=6)
    ax.axhline(0, color="#444", lw=1.0, zorder=4)
    ax.scatter([SRC[0]], [SRC[2]], c="cyan", s=40, zorder=7, label="Acoustic source (Curle proxy)")
    for name, p in OBS.items():
        if abs(p[1]) < 1e-9:
            ax.scatter([p[0]], [p[2]], c="lime", s=36, zorder=7, edgecolors="k", linewidths=0.4)
            ax.annotate(name, (p[0], p[2]), textcoords="offset points", xytext=(4, 6),
                        fontsize=8, color="w", zorder=8)
    ax.set_xlim(-0.3, 6.8)
    ax.set_ylim(0, 2.0)
    ax.set_aspect("equal")
    ax.set_xlabel("x [m]")
    ax.set_ylabel("z [m]")
    ax.set_title("SPL contour — symmetry plane (y = 0)\nAhmed 25° · compact Curle dipole proxy (demo-calibrated)")
    fig.colorbar(cf, ax=ax, pad=0.02, fraction=0.046).set_label("SPL [dB re 20 µPa]")
    ax.legend(loc="upper right", fontsize=8, framealpha=0.35, labelcolor="w", facecolor="#333")
    fig.tight_layout()
    path = out / "spl_contour_symmetry.png"
    fig.savefig(path, dpi=160)
    fig.savefig(out / "spl_contour_symmetry.svg")
    plt.close(fig)
    return path


def plot_horizontal(out: Path) -> Path:
    x = np.linspace(-0.5, 7.0, 420)
    y = np.linspace(-2.2, 2.2, 280)
    X, Y = np.meshgrid(x, y)
    Z = np.full_like(X, 0.20)
    SPL = spl_field(X, Y, Z)
    foot = (X >= 0.0) & (X <= L) & (Y >= -W / 2) & (Y <= W / 2)
    SPL_plot = np.ma.array(SPL, mask=foot)

    levels = np.linspace(55, 100, 19)
    cmap = plt.colormaps.get_cmap("magma")
    fig, ax = plt.subplots(figsize=(11, 5.2))
    cf = ax.contourf(X, Y, SPL_plot, levels=levels, cmap=cmap, extend="both")
    ax.contour(X, Y, SPL_plot, levels=levels[::2], colors="w", linewidths=0.35, alpha=0.45)
    ax.add_patch(Rectangle((0.0, -W / 2), L, W, facecolor="#1a1a1a", edgecolor="w", lw=1.0, zorder=5))
    ax.scatter([SRC[0]], [SRC[1]], c="cyan", s=40, zorder=7, label="Source")
    for name, p in OBS.items():
        ax.scatter([p[0]], [p[1]], c="lime", s=36, zorder=7, edgecolors="k", linewidths=0.4)
        ax.annotate(name, (p[0], p[1]), textcoords="offset points", xytext=(4, 4),
                    fontsize=7.5, color="w", zorder=8)
    ax.text(
        3.2, -1.85,
        "OASPL demo anchors: 1 m = 95.1 dB · 3 m = 85.6 dB · 5 m = 81.2 dB",
        color="w", fontsize=8, ha="center",
        bbox=dict(boxstyle="round,pad=0.3", fc="#00000088", ec="none"),
    )
    ax.set_xlim(-0.3, 6.8)
    ax.set_ylim(-2.0, 2.0)
    ax.set_aspect("equal")
    ax.set_xlabel("x [m]")
    ax.set_ylabel("y [m]")
    ax.set_title("SPL contour — horizontal plane (z = 0.20 m)\nAhmed 25° · compact Curle dipole proxy (demo-calibrated)")
    fig.colorbar(cf, ax=ax, pad=0.02, fraction=0.046).set_label("SPL [dB re 20 µPa]")
    ax.legend(loc="upper right", fontsize=8, framealpha=0.35, labelcolor="w", facecolor="#333")
    fig.tight_layout()
    path = out / "spl_contour_horizontal.png"
    fig.savefig(path, dpi=160)
    fig.savefig(out / "spl_contour_horizontal.svg")
    plt.close(fig)
    return path


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-dir", type=Path, default=Path("Reports/caa/figures"))
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    p1 = plot_symmetry(args.out_dir)
    p2 = plot_horizontal(args.out_dir)
    print("wrote", p1)
    print("wrote", p2)
    print("Observer SPL from contour field:")
    for name, p in OBS.items():
        s = float(spl_field(np.array([p[0]]), np.array([p[1]]), np.array([p[2]]))[0])
        print(f"  {name:10s}  {s:5.1f} dB")


if __name__ == "__main__":
    main()
