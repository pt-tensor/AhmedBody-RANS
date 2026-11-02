#!/usr/bin/env python3
"""
Ahmed-body CAA post-processing: pressure time histories → SPL spectra.

Reads OpenFOAM probes functionObject output (kinematic pressure p [m²/s²]),
converts to acoustic Pascal via ρ∞, then computes:

  1. Welch PSD of p'(t)
  2. Narrow-band SPL(f) = 10·log10(Gxx(f)·Δf / p_ref²)  [dB, re 20 µPa]
  3. 1/3-octave band SPL aggregation (0 – f_max)

Also supports:
  --demo          synthesise a bluff-body-like signal (no CFD required)
  --surface-dir   optional Curle far-field from raw surface pressure dumps

Target: OpenFOAM ESI v2312/v2406 probe layout
  postProcessing/acousticProbes/<time>/p

Usage:
  python3 scripts/caa/compute_spl.py --demo
  python3 scripts/caa/compute_spl.py --probe-dir postProcessing/acousticProbes
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

try:
    from scipy import signal
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "scipy is required: pip install -r scripts/caa/requirements-caa.txt"
    ) from exc

try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except ImportError:  # pragma: no cover
    plt = None


# --- Physical / analysis defaults ------------------------------------------------
RHO_INF = 1.225          # kg/m³  (air) — converts kinematic p → Pa
P_REF = 20e-6            # Pa
C0 = 343.0               # m/s
F_MAX = 2500.0           # Hz
FS_TARGET = 50000.0      # Hz (matches writeInterval 2e-5)
U_INF = 40.0             # m/s
H_REF = 0.288            # m (Ahmed height)


def kinematic_to_pa(p_kin: np.ndarray, rho: float = RHO_INF) -> np.ndarray:
    """OpenFOAM incompressible p is p/ρ [m²/s²]; acoustic pressure [Pa] = ρ·p."""
    return rho * p_kin


def read_openfoam_probe_file(path: Path) -> Tuple[np.ndarray, np.ndarray]:
    """
    Parse probes output: '# Probe 0 (x y z)' header then 'Time p0 p1 ...'
    Returns (time, pressure_array[n_time, n_probes]) as kinematic pressure.
    """
    times: List[float] = []
    rows: List[List[float]] = []
    with path.open() as fh:
        for line in fh:
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            parts = s.split()
            if len(parts) < 2:
                continue
            try:
                t = float(parts[0])
                vals = [float(v) for v in parts[1:]]
            except ValueError:
                continue
            times.append(t)
            rows.append(vals)
    if not times:
        raise ValueError(f"No probe samples in {path}")
    return np.asarray(times), np.asarray(rows)


def find_probe_pressure_files(probe_dir: Path) -> List[Path]:
    """Collect all 'p' files under postProcessing/acousticProbes/**/p."""
    files = sorted(probe_dir.glob("**/p"))
    # Prefer leaf files named exactly 'p'
    files = [f for f in files if f.is_file()]
    return files


def load_probe_series(
    probe_dir: Path,
) -> Tuple[np.ndarray, np.ndarray]:
    """Concatenate probe files across time directories (latestTime folders)."""
    files = find_probe_pressure_files(probe_dir)
    if not files:
        raise FileNotFoundError(
            f"No probe pressure files under {probe_dir}. "
            "Run Stage 3 or use --demo."
        )
    t_all: List[np.ndarray] = []
    p_all: List[np.ndarray] = []
    for f in files:
        t, p = read_openfoam_probe_file(f)
        t_all.append(t)
        p_all.append(p)
    t = np.concatenate(t_all)
    p = np.concatenate(p_all, axis=0)
    order = np.argsort(t)
    t, p = t[order], p[order]
    # Drop duplicate times from overlapping reconstruct windows
    _, uniq = np.unique(t, return_index=True)
    return t[uniq], p[uniq]


def estimate_fs(t: np.ndarray) -> float:
    dt = np.diff(t)
    dt = dt[dt > 0]
    if dt.size == 0:
        raise ValueError("Cannot estimate sample rate from time vector")
    return float(1.0 / np.median(dt))


def welch_spl(
    p_pa: np.ndarray,
    fs: float,
    f_max: float = F_MAX,
    nperseg: Optional[int] = None,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Welch PSD → narrow-band SPL [dB].

    Returns f [Hz], Gxx [Pa²/Hz], SPL_nb [dB] where
      SPL_nb = 10 log10( Gxx · Δf / p_ref² )
    with Δf = fs / nperseg (Welch frequency bin width).
    """
    if nperseg is None:
        # ~1 Hz resolution when possible; clamp for short signals
        nperseg = int(2 ** np.floor(np.log2(max(fs, 8))))
        nperseg = int(min(nperseg, max(256, len(p_pa) // 4)))
        nperseg = max(256, nperseg)

    # Remove mean (acoustic fluctuating pressure)
    p = p_pa - np.mean(p_pa)

    f, gxx = signal.welch(
        p,
        fs=fs,
        window="hann",
        nperseg=nperseg,
        noverlap=nperseg // 2,
        detrend="constant",
        scaling="density",
    )

    df = f[1] - f[0] if len(f) > 1 else fs / nperseg
    # Narrow-band SPL in each Welch bin
    spl = 10.0 * np.log10(np.maximum(gxx * df, 1e-30) / P_REF**2)

    mask = f <= f_max + 1e-9
    return f[mask], gxx[mask], spl[mask]


def third_octave_edges(f_min: float = 10.0, f_max: float = F_MAX) -> np.ndarray:
    """Standard 1/3-octave centre frequencies and band edges (IEC / ANSI)."""
    # Preferred centre frequencies
    centres = []
    # Generate G = 10^(0.1) geometric sequence around 1000 Hz
    k_start = int(math.floor(10.0 * math.log10(f_min / 1000.0)))
    k_end = int(math.ceil(10.0 * math.log10(f_max / 1000.0)))
    for k in range(k_start, k_end + 1):
        fc = 1000.0 * (10.0 ** (0.1 * k))
        if f_min <= fc <= f_max:
            centres.append(fc)
    centres = np.asarray(centres)
    # Band edges: fc / 2^(1/6) .. fc * 2^(1/6)
    factor = 2.0 ** (1.0 / 6.0)
    f_lo = centres / factor
    f_hi = centres * factor
    return centres, f_lo, f_hi


def aggregate_third_octave(
    f: np.ndarray,
    gxx: np.ndarray,
    f_max: float = F_MAX,
) -> Tuple[np.ndarray, np.ndarray]:
    """Integrate PSD into 1/3-octave bands → band SPL [dB]."""
    centres, f_lo, f_hi = third_octave_edges(f_min=max(f[1], 10.0), f_max=f_max)
    band_spl = np.full(centres.shape, np.nan)
    _trapz = getattr(np, "trapezoid", None) or np.trapz
    for i, (lo, hi) in enumerate(zip(f_lo, f_hi)):
        m = (f >= lo) & (f < hi)
        if np.count_nonzero(m) < 2:
            continue
        power = _trapz(gxx[m], f[m])
        if power <= 0.0:
            continue
        band_spl[i] = 10.0 * np.log10(power / P_REF**2)
    return centres, band_spl


def overall_spl(p_pa: np.ndarray) -> float:
    p = p_pa - np.mean(p_pa)
    p_rms = float(np.sqrt(np.mean(p**2)))
    return 20.0 * np.log10(max(p_rms, 1e-30) / P_REF)


def curle_farfield_point(
    times: np.ndarray,
    # surface: list of (area_vec outward [m²], p_kin history [m²/s²])
    faces: Sequence[Tuple[np.ndarray, np.ndarray]],
    observer: np.ndarray,
    face_centres: Sequence[np.ndarray],
    rho: float = RHO_INF,
    c0: float = C0,
) -> np.ndarray:
    """
    Compact low-Mach Curle dipole approximation (solid-surface FW-H limit):

      p'(x,t) ≈ (1/(4π c0)) · (r_i / r²) · ∂F_i/∂t  (retarded, far-field)

    with F_i = ∫ p n_i dS  (loading noise; quadrupole neglected at Ma≪1).

    This is a practical engineering estimator for scripting — for production
    certification use libAcoustics Farassat 1A (system/acousticFWH).
    """
    n_t = len(times)
    force = np.zeros((n_t, 3))
    for area_vec, p_kin in faces:
        # area_vec = n̂ · A
        force += np.outer(p_kin, area_vec) * rho  # [N]

    # dF/dt
    dt = np.gradient(times)
    dFdt = np.gradient(force, axis=0) / dt[:, None]

    # Use mean face centre as source origin for compact approximation
    src = np.mean(np.asarray(face_centres), axis=0)
    r_vec = observer - src
    r = np.linalg.norm(r_vec)
    if r < 1e-9:
        raise ValueError("Observer coincides with source")
    r_hat = r_vec / r

    # Neglect retarded-time interpolation for compact source (valid if
    # source region ≪ λ_min); apply amplitude + propagation delay globally
    delay = r / c0
    p_ff = (r_hat @ dFdt.T) / (4.0 * math.pi * c0 * r)

    # Shift by retarded time (zero-pad)
    t_obs = times + delay
    # Resample onto original time base for convenience
    p_on_src_time = np.interp(times, t_obs, p_ff, left=0.0, right=0.0)
    return p_on_src_time


def synthesise_demo(
    fs: float = FS_TARGET,
    duration: float = 0.4,
    seed: int = 42,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Synthetic multi-probe pressure [Pa] mimicking Ahmed wake aeroacoustics:
      - broadband turbulence (-5/3-ish roll-off via coloured noise)
      - tonal content from vortex shedding St≈0.2 → f = St·U/H ≈ 28 Hz
      - slant-edge secondary ~ St≈0.5
    """
    rng = np.random.default_rng(seed)
    n = int(fs * duration)
    t = np.arange(n) / fs
    st1 = 0.20
    st2 = 0.50
    f1 = st1 * U_INF / H_REF
    f2 = st2 * U_INF / H_REF

    # Coloured noise via FFT shaping
    white = rng.standard_normal(n)
    spec = np.fft.rfft(white)
    freqs = np.fft.rfftfreq(n, 1.0 / fs)
    shape = np.ones_like(freqs)
    shape[1:] = (freqs[1:] / 50.0) ** (-5.0 / 6.0)  # ~ -5/3 PSD slope
    shape[0] = 0.0
    coloured = np.fft.irfft(spec * shape, n=n)
    coloured /= np.std(coloured) + 1e-12

    probes = []
    distances = [1.0, 3.0, 5.0, 1.0, 1.0, 3.0, 3.0, 5.0, 5.0]
    for d in distances:
        amp = 2.0 / d  # geometric spherical spreading proxy [Pa]
        tone = (
            0.6 * amp * np.sin(2 * np.pi * f1 * t)
            + 0.25 * amp * np.sin(2 * np.pi * f2 * t)
        )
        noise = 0.35 * amp * coloured
        probes.append(tone + noise)
    p = np.column_stack(probes)
    return t, p


def save_spectrum_csv(
    path: Path,
    f: np.ndarray,
    spl: np.ndarray,
    gxx: np.ndarray,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["freq_Hz", "SPL_dB", "Gxx_Pa2_per_Hz"])
        for fi, si, gi in zip(f, spl, gxx):
            w.writerow([f"{fi:.6f}", f"{si:.4f}", f"{gi:.8e}"])


def save_third_octave_csv(path: Path, fc: np.ndarray, spl: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["fc_Hz", "SPL_third_octave_dB"])
        for a, b in zip(fc, spl):
            if np.isnan(b):
                continue
            w.writerow([f"{a:.6f}", f"{b:.4f}"])


def plot_spectra(
    out_dir: Path,
    probe_id: int,
    f: np.ndarray,
    spl_nb: np.ndarray,
    fc: np.ndarray,
    spl_to: np.ndarray,
    oaspl: float,
) -> None:
    if plt is None:
        return
    out_dir.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.semilogx(f[1:], spl_nb[1:], lw=0.9, color="#1f4e79", label="Narrow-band")
    ax.step(fc, spl_to, where="mid", color="#c45c26", lw=1.6, label="1/3-octave")
    ax.set_xlim(10, F_MAX)
    ax.set_xlabel("Frequency [Hz]")
    ax.set_ylabel("SPL [dB re 20 µPa]")
    ax.set_title(f"Probe {probe_id} — OASPL = {oaspl:.1f} dB")
    ax.grid(True, which="both", ls=":", alpha=0.6)
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(out_dir / f"probe_{probe_id:02d}_spl.svg")
    fig.savefig(out_dir / f"probe_{probe_id:02d}_spl.png", dpi=140)
    plt.close(fig)


def process_probe_matrix(
    t: np.ndarray,
    p_pa: np.ndarray,
    out_dir: Path,
    f_max: float,
    label: str,
) -> Dict:
    fs = estimate_fs(t)
    summary = {
        "label": label,
        "fs_Hz": fs,
        "duration_s": float(t[-1] - t[0]),
        "n_samples": int(p_pa.shape[0]),
        "n_probes": int(p_pa.shape[1]),
        "probes": [],
    }
    fig_dir = out_dir / "figures"
    for i in range(p_pa.shape[1]):
        f, gxx, spl = welch_spl(p_pa[:, i], fs=fs, f_max=f_max)
        fc, spl_to = aggregate_third_octave(f, gxx, f_max=f_max)
        oaspl = overall_spl(p_pa[:, i])
        save_spectrum_csv(out_dir / f"probe_{i:02d}_narrowband.csv", f, spl, gxx)
        save_third_octave_csv(out_dir / f"probe_{i:02d}_third_octave.csv", fc, spl_to)
        plot_spectra(fig_dir, i, f, spl, fc, spl_to, oaspl)
        valid = np.isfinite(spl_to)
        if np.any(valid):
            peak_spl = float(np.max(spl_to[valid]))
            peak_fc = float(fc[valid][np.argmax(spl_to[valid])])
        else:
            peak_spl = float("nan")
            peak_fc = float("nan")
        summary["probes"].append(
            {
                "probe": i,
                "OASPL_dB": oaspl,
                "SPL_peak_dB": peak_spl,
                "fc_peak_Hz": peak_fc,
            }
        )
        if np.isfinite(peak_spl):
            print(
                f"  Probe {i:02d}: OASPL={oaspl:6.1f} dB | "
                f"1/3-oct peak {peak_spl:.1f} dB @ {peak_fc:.1f} Hz"
            )
        else:
            print(f"  Probe {i:02d}: OASPL={oaspl:6.1f} dB | 1/3-oct: insufficient data")
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2))
    return summary


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--probe-dir", type=Path, default=Path("postProcessing/acousticProbes"))
    ap.add_argument("--out-dir", type=Path, default=Path("Reports/caa"))
    ap.add_argument("--f-max", type=float, default=F_MAX)
    ap.add_argument("--rho", type=float, default=RHO_INF)
    ap.add_argument("--demo", action="store_true", help="Synthetic signal (no CFD)")
    ap.add_argument("--demo-duration", type=float, default=0.4)
    args = ap.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("Ahmed Body CAA — SPL post-processing")
    print("=" * 60)

    if args.demo:
        print("[demo] synthesising bluff-body-like microphone signals …")
        t, p_pa = synthesise_demo(duration=args.demo_duration)
        label = "demo_synthetic"
    else:
        print(f"[cfd] loading probes from {args.probe_dir}")
        t, p_kin = load_probe_series(args.probe_dir)
        p_pa = kinematic_to_pa(p_kin, rho=args.rho)
        label = "cfd_probes"
        print(f"  converted kinematic p → Pa with ρ∞={args.rho}")

    summary = process_probe_matrix(t, p_pa, args.out_dir, args.f_max, label)
    print("-" * 60)
    print(f"fs ≈ {summary['fs_Hz']:.1f} Hz | T = {summary['duration_s']:.3f} s")
    print(f"Wrote spectra → {args.out_dir}/")
    print("Done.")


if __name__ == "__main__":
    main()
