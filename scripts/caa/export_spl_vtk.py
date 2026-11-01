#!/usr/bin/env python3
"""
Export demo-calibrated Curle-dipole SPL field as legacy VTK STRUCTURED_POINTS
for reliable ParaView 5.11 loading (ASCII).

Usage:
  python3 scripts/caa/export_spl_vtk.py
  xvfb-run -a pvpython scripts/caa/paraview_capture_spl.py
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

PREF = 20e-6
L, H = 1.044, 0.288
SRC = np.array([L + 0.05, 0.0, H * 0.45 + 0.05])
OBS_1M = np.array([2.044, 0.0, 0.20])
OASPL_1M = 95.1


def spl_field(X: np.ndarray, Y: np.ndarray, Z: np.ndarray) -> np.ndarray:
    p_rms_1m = PREF * 10 ** (OASPL_1M / 20)
    rx, ry, rz = X - SRC[0], Y - SRC[1], Z - SRC[2]
    r = np.maximum(np.sqrt(rx * rx + ry * ry + rz * rz), 0.08)
    diri = 0.75 * np.abs(rx / r) + 0.25 * (0.6 + 0.4 * np.abs(rz / r))
    r_ref = float(np.linalg.norm(OBS_1M - SRC))
    dx = (OBS_1M[0] - SRC[0]) / r_ref
    dz = (OBS_1M[2] - SRC[2]) / r_ref
    diri_ref = 0.75 * abs(dx) + 0.25 * (0.6 + 0.4 * abs(dz))
    amp = p_rms_1m * r_ref / max(diri_ref, 1e-6)
    p_rms = np.maximum(amp * diri / r, PREF * 10 ** (35 / 20))
    return 20.0 * np.log10(p_rms / PREF)


def write_structured_points(path: Path, spl: np.ndarray, origin, spacing) -> None:
    nx, ny, nz = spl.shape
    flat = spl.astype(np.float32).ravel(order="F")
    ox, oy, oz = origin
    sx, sy, sz = spacing
    with path.open("w") as f:
        f.write("# vtk DataFile Version 3.0\n")
        f.write("Ahmed body SPL_dB Curle dipole demo\n")
        f.write("ASCII\n")
        f.write("DATASET STRUCTURED_POINTS\n")
        f.write(f"DIMENSIONS {nx} {ny} {nz}\n")
        f.write(f"ORIGIN {ox} {oy} {oz}\n")
        f.write(f"SPACING {sx} {sy} {sz}\n")
        f.write(f"POINT_DATA {flat.size}\n")
        f.write("SCALARS SPL_dB float 1\n")
        f.write("LOOKUP_TABLE default\n")
        for i in range(0, flat.size, 8):
            chunk = flat[i : i + 8]
            f.write(" ".join(f"{v:.6f}" for v in chunk) + "\n")


def write_observers(path: Path) -> None:
    coords = [
        (2.044, 0.0, 0.20),
        (4.044, 0.0, 0.20),
        (6.044, 0.0, 0.20),
        (2.044, 1.0, 0.20),
        (2.044, -1.0, 0.20),
        (float(SRC[0]), float(SRC[1]), float(SRC[2])),
    ]
    with path.open("w") as f:
        f.write("# vtk DataFile Version 3.0\nObservers\nASCII\nDATASET POLYDATA\n")
        f.write(f"POINTS {len(coords)} float\n")
        for p in coords:
            f.write(f"{p[0]} {p[1]} {p[2]}\n")
        f.write(f"VERTICES {len(coords)} {2 * len(coords)}\n")
        for i in range(len(coords)):
            f.write(f"1 {i}\n")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-dir", type=Path, default=Path("Reports/caa/paraview"))
    ap.add_argument("--nx", type=int, default=160)
    ap.add_argument("--ny", type=int, default=90)
    ap.add_argument("--nz", type=int, default=60)
    args = ap.parse_args()

    xmin, xmax = -0.4, 7.0
    ymin, ymax = -2.2, 2.2
    zmin, zmax = 0.0, 2.2
    sx = (xmax - xmin) / (args.nx - 1)
    sy = (ymax - ymin) / (args.ny - 1)
    sz = (zmax - zmin) / (args.nz - 1)
    x = np.linspace(xmin, xmax, args.nx)
    y = np.linspace(ymin, ymax, args.ny)
    z = np.linspace(zmin, zmax, args.nz)
    X, Y, Z = np.meshgrid(x, y, z, indexing="ij")
    SPL = spl_field(X, Y, Z)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    vtk_path = args.out_dir / "spl_field.vtk"
    write_structured_points(vtk_path, SPL, (xmin, ymin, zmin), (sx, sy, sz))
    write_observers(args.out_dir / "observers.vtk")
    print(f"wrote {vtk_path}  SPL [{float(SPL.min()):.1f}, {float(SPL.max()):.1f}] dB")
    print(f"wrote {args.out_dir / 'observers.vtk'}")


if __name__ == "__main__":
    main()
