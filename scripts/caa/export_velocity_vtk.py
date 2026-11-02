#!/usr/bin/env python3
"""
Export a representative Ahmed 25° velocity field as legacy VTK for ParaView.

This is NOT a solved OpenFOAM IDDES field — it is a physics-informed demo
field used when a transient solution is unavailable. Topology matches the
classic 25° attached-slant / C-pillar vortex / base wake picture:

  - freestream U∞ = 40 m/s
  - nose stagnation + roof/underbody acceleration
  - base recirculation bubble
  - slant shear layer
  - recovering wake

Usage:
  python3 scripts/caa/export_velocity_vtk.py
  xvfb-run -a pvpython scripts/caa/paraview_capture_velocity.py
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

U_INF = 40.0
L = 1.044
H = 0.288
W = 0.389
Z0 = 0.05  # underbody clearance (approx)


def body_occupancy(X, Y, Z):
    """Rough solid mask for Ahmed-like footprint (nose@0 after STL +0.1 shift)."""
    inside = (
        (X >= 0.0)
        & (X <= L)
        & (np.abs(Y) <= W / 2)
        & (Z >= Z0)
        & (Z <= Z0 + H)
    )
    # 25° rear slant cut: roof drops for x > slant start
    slant_start = L - 0.222
    z_roof = Z0 + H - np.maximum(X - slant_start, 0.0) * np.tan(np.deg2rad(25.0))
    inside &= Z <= z_roof + 1e-6
    return inside


def velocity_field(X, Y, Z, instantaneous: bool = False, seed: int = 7):
    """Return U,V,W components [m/s]."""
    solid = body_occupancy(X, Y, Z)

    # Base freestream + ground BL (approx power-law near z=0)
    z_plus = np.maximum(Z, 1e-4)
    bl = np.clip((z_plus / 0.15) ** 0.14, 0.0, 1.0)
    U = U_INF * bl * np.ones_like(X)
    V = np.zeros_like(X)
    W = np.zeros_like(X)

    # Nose stagnation / acceleration (potential-like dipole correction)
    # Source near nose centre
    xn, zn = 0.05, Z0 + 0.5 * H
    rn = np.sqrt((X - xn) ** 2 + (Z - zn) ** 2 + (0.35 * Y) ** 2) + 0.08
    U -= 18.0 * (X - xn) / rn**2
    W -= 10.0 * (Z - zn) / rn**2

    # Roof acceleration
    roof = (X > 0.15) & (X < 0.85) & (Z > Z0 + 0.7 * H) & (np.abs(Y) < W / 2 + 0.15)
    U = np.where(roof, U * 1.15, U)

    # Underbody channel
    under = (X > 0.0) & (X < L) & (Z < Z0 + 0.08) & (np.abs(Y) < W / 2)
    U = np.where(under, U_INF * 0.85, U)

    # Base wake recirculation (toroidal-ish bubble behind base)
    xb, zb = L + 0.18, Z0 + 0.35 * H
    rw = np.sqrt((X - xb) ** 2 + ((Z - zb) / 0.55) ** 2 + (Y / 0.45) ** 2)
    wake = np.exp(-(rw**2) / 0.22)
    U -= (0.95 * U_INF) * wake
    # Reverse flow core
    U = np.where(rw < 0.35, U - 12.0 * np.exp(-(rw**2) / 0.05), U)
    W += 8.0 * wake * (Z - zb)

    # Slant shear layer (25°): elevated mixing above slant
    slant_x0 = L - 0.222
    along = (X - slant_x0) * np.cos(np.deg2rad(25)) + (Z - (Z0 + H)) * np.sin(
        np.deg2rad(25)
    )
    normal = -(X - slant_x0) * np.sin(np.deg2rad(25)) + (Z - (Z0 + H)) * np.cos(
        np.deg2rad(25)
    )
    shear = np.exp(-(normal**2) / 0.01) * np.clip(1.0 - along / 1.2, 0, 1) * (
        X > slant_x0 - 0.05
    )
    U -= 10.0 * shear
    W -= 6.0 * shear

    # C-pillar / longitudinal vortices (pair)
    for sign in (+1.0, -1.0):
        yc = sign * 0.16
        xc, zc = L - 0.05, Z0 + 0.55 * H
        rc = np.sqrt((X - xc) ** 2 + (Y - yc) ** 2 + ((Z - zc) / 0.7) ** 2) + 0.05
        Gamma = -sign * 3.5
        V += -Gamma * (Z - zc) / rc**2 * np.exp(-(rc**2) / 0.25)
        W += Gamma * (Y - yc) / rc**2 * np.exp(-(rc**2) / 0.25)
        U -= 2.0 * np.exp(-(rc**2) / 0.15)

    # Far wake recovery
    recovery = 1.0 - np.exp(-np.maximum(X - L, 0.0) / 2.5)
    U = U_INF * recovery + U * (1.0 - 0.35 * recovery)

    if instantaneous:
        # LES-like broadband fluctuations in wake (visual only)
        rng = np.random.default_rng(seed)
        noise = rng.normal(0.0, 1.0, size=X.shape)
        # Spatially smooth via coarse FFT-ish: just local kernel-ish with phase
        kx = 8.0 * np.pi / L
        phase = kx * X + 6.0 * Y + 5.0 * Z
        fluct = 0.12 * U_INF * wake * (0.7 * np.sin(phase) + 0.3 * noise)
        U += fluct
        V += 0.45 * fluct * np.sin(phase + 1.3)
        W += 0.35 * fluct * np.cos(phase + 0.7)

    # Solid body → zero
    U = np.where(solid, 0.0, U)
    V = np.where(solid, 0.0, V)
    W = np.where(solid, 0.0, W)

    # Clip extremes
    U = np.clip(U, -15.0, 65.0)
    return U.astype(np.float32), V.astype(np.float32), W.astype(np.float32)


def write_vtk(path: Path, U, V, W, origin, spacing, write_vectors: bool = False):
    nx, ny, nz = U.shape
    mag = np.sqrt(U * U + V * V + W * W)
    # VTK STRUCTURED_POINTS: x fastest
    m_f = mag.astype(np.float32).ravel(order="F")
    ox, oy, oz = origin
    sx, sy, sz = spacing
    n = m_f.size
    with path.open("w") as f:
        f.write("# vtk DataFile Version 3.0\n")
        f.write("Ahmed 25deg representative velocity (IDDES-demo)\n")
        f.write("ASCII\n")
        f.write("DATASET STRUCTURED_POINTS\n")
        f.write(f"DIMENSIONS {nx} {ny} {nz}\n")
        f.write(f"ORIGIN {ox} {oy} {oz}\n")
        f.write(f"SPACING {sx} {sy} {sz}\n")
        f.write(f"POINT_DATA {n}\n")
        f.write("SCALARS U_magnitude float 1\n")
        f.write("LOOKUP_TABLE default\n")
        for i in range(0, n, 8):
            f.write(" ".join(f"{v:.5f}" for v in m_f[i : i + 8]) + "\n")
        if write_vectors:
            u_f = U.ravel(order="F")
            v_f = V.ravel(order="F")
            w_f = W.ravel(order="F")
            f.write("VECTORS U float\n")
            for i in range(n):
                f.write(f"{u_f[i]:.5f} {v_f[i]:.5f} {w_f[i]:.5f}\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-dir", type=Path, default=Path("Reports/caa/paraview"))
    ap.add_argument("--nx", type=int, default=160)
    ap.add_argument("--ny", type=int, default=80)
    ap.add_argument("--nz", type=int, default=70)
    ap.add_argument("--instantaneous", action="store_true", help="Add LES-like fluctuations")
    args = ap.parse_args()

    xmin, xmax = -0.5, 5.0
    ymin, ymax = -1.2, 1.2
    zmin, zmax = 0.0, 1.6
    sx = (xmax - xmin) / (args.nx - 1)
    sy = (ymax - ymin) / (args.ny - 1)
    sz = (zmax - zmin) / (args.nz - 1)
    x = np.linspace(xmin, xmax, args.nx)
    y = np.linspace(ymin, ymax, args.ny)
    z = np.linspace(zmin, zmax, args.nz)
    X, Y, Z = np.meshgrid(x, y, z, indexing="ij")
    U, V, W = velocity_field(X, Y, Z, instantaneous=args.instantaneous)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    tag = "instantaneous" if args.instantaneous else "mean"
    path = args.out_dir / f"velocity_{tag}.vtk"
    write_vtk(path, U, V, W, (xmin, ymin, zmin), (sx, sy, sz))
    mag = np.sqrt(U * U + V * V + W * W)
    print(f"wrote {path}")
    print(f"  |U| range [{float(mag.min()):.2f}, {float(mag.max()):.2f}] m/s")
    print("  NOTE: representative demo field for IDDES visualization — not a CFD solve.")


if __name__ == "__main__":
    main()
