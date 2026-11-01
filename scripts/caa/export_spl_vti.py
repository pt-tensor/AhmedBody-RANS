#!/usr/bin/env python3
"""
Export a demo-calibrated Curle-dipole SPL field as VTK ImageData (.vti)
for ParaView visualization.

Usage:
  python3 scripts/caa/export_spl_vti.py --out Reports/caa/paraview/spl_field.vti
"""

from __future__ import annotations

import argparse
import struct
import zlib
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
    return 20.0 * np.log10(p_rms / PREF).astype(np.float32)


def write_vti(path: Path, spl: np.ndarray, origin, spacing) -> None:
    """Write VTK ImageData XML (appended binary, zlib) — ParaView friendly."""
    nz, ny, nx = spl.shape  # z-y-x layout for VTK ImageData
    assert spl.dtype == np.float32
    flat = np.ascontiguousarray(spl.ravel(order="F"))  # VTK expects Fortran order x-fastest
    # Actually VTK ImageData point data is x varying fastest: index = i + j*nx + k*nx*ny
    # Our meshgrid indexing: X[k,j,i] if we build with indexing='ij' differently.
    # We build with meshgrid(..., indexing='xy') then transpose carefully below.

    raw = flat.tobytes()
    compressed = zlib.compress(raw)
    header = struct.pack("<III", 1, len(raw), len(compressed))  # num blocks, usize, csize (single block)
    payload = header + compressed

    ox, oy, oz = origin
    sx, sy, sz = spacing
    xml = f"""<?xml version="1.0"?>
<VTKFile type="ImageData" version="1.0" byte_order="LittleEndian" header_type="UInt32" compressor="vtkZLibDataCompressor">
  <ImageData WholeExtent="0 {nx-1} 0 {ny-1} 0 {nz-1}" Origin="{ox} {oy} {oz}" Spacing="{sx} {sy} {sz}">
    <Piece Extent="0 {nx-1} 0 {ny-1} 0 {nz-1}">
      <PointData Scalars="SPL_dB">
        <DataArray type="Float32" Name="SPL_dB" format="appended" offset="0" RangeMin="{float(spl.min()):.6f}" RangeMax="{float(spl.max()):.6f}"/>
      </PointData>
      <CellData/>
    </Piece>
  </ImageData>
  <AppendedData encoding="raw">
_"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as fh:
        fh.write(xml.encode("ascii"))
        fh.write(payload)
        fh.write(b"\n  </AppendedData>\n</VTKFile>\n")


def write_observers_vtp(path: Path) -> None:
    observers = [
        (2.044, 0.0, 0.20, "wake_1m"),
        (4.044, 0.0, 0.20, "wake_3m"),
        (6.044, 0.0, 0.20, "wake_5m"),
        (2.044, 1.0, 0.20, "lat_p1m"),
        (2.044, -1.0, 0.20, "lat_m1m"),
        (SRC[0], SRC[1], SRC[2], "source"),
    ]
    n = len(observers)
    pts = "".join(f"{x} {y} {z}\n" for x, y, z, _ in observers)
    conn = "".join(f"{i}\n" for i in range(n))
    offs = "".join(f"{i+1}\n" for i in range(n))
    labels = "".join(f"{name}\n" for *_, name in observers)
    xml = f"""<?xml version="1.0"?>
<VTKFile type="PolyData" version="0.1" byte_order="LittleEndian">
  <PolyData>
    <Piece NumberOfPoints="{n}" NumberOfVerts="{n}" NumberOfLines="0" NumberOfStrips="0" NumberOfPolys="0">
      <Points>
        <DataArray type="Float32" NumberOfComponents="3" format="ascii">
{pts}        </DataArray>
      </Points>
      <Verts>
        <DataArray type="Int32" Name="connectivity" format="ascii">
{conn}        </DataArray>
        <DataArray type="Int32" Name="offsets" format="ascii">
{offs}        </DataArray>
      </Verts>
      <PointData>
        <DataArray type="String" Name="label" format="ascii">
{labels}        </DataArray>
      </PointData>
    </Piece>
  </PolyData>
</VTKFile>
"""
    path.write_text(xml)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=Path("Reports/caa/paraview/spl_field.vti"))
    ap.add_argument("--nx", type=int, default=220)
    ap.add_argument("--ny", type=int, default=120)
    ap.add_argument("--nz", type=int, default=80)
    args = ap.parse_args()

    # Domain covering Ahmed body + wake observers
    xmin, xmax = -0.4, 7.0
    ymin, ymax = -2.2, 2.2
    zmin, zmax = 0.0, 2.2
    sx = (xmax - xmin) / (args.nx - 1)
    sy = (ymax - ymin) / (args.ny - 1)
    sz = (zmax - zmin) / (args.nz - 1)

    x = np.linspace(xmin, xmax, args.nx)
    y = np.linspace(ymin, ymax, args.ny)
    z = np.linspace(zmin, zmax, args.nz)
    # VTK: x fastest → array shape (nz, ny, nx) with Fortran flatten
    X, Y, Z = np.meshgrid(x, y, z, indexing="ij")  # shapes (nx,ny,nz)
    SPL = spl_field(X, Y, Z)  # (nx,ny,nz)
    # Reorder to (nz,ny,nx) then Fortran-ravel ≡ x-fastest linearization
    spl_zyx = np.transpose(SPL, (2, 1, 0)).astype(np.float32)

    write_vti(args.out, spl_zyx, origin=(xmin, ymin, zmin), spacing=(sx, sy, sz))
    obs_path = args.out.with_name("observers.vtp")
    write_observers_vtp(obs_path)
    print(f"wrote {args.out}  SPL range [{float(SPL.min()):.1f}, {float(SPL.max()):.1f}] dB")
    print(f"wrote {obs_path}")


if __name__ == "__main__":
    main()
