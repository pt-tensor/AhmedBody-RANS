# Hybrid CAA Methodology — Ahmed 25° Body

**Target OpenFOAM:** ESI **v2312 / v2406** (dictionaries also valid on **v2206**).  
**Solver chain:** `simpleFoam` (RANS) → `pimpleFoam` (IDDES) → Python / optional `libAcoustics` FW-H.

## Flow & acoustics setup

| Parameter | Value |
| --- | --- |
| Geometry | Standard Ahmed body, slant **25°** |
| Characteristic height \(H\) | 0.288 m |
| \(U_\infty\) | 40 m/s (Ma ≈ 0.117) |
| Fluid | Air, \(\rho=1.225\,\mathrm{kg/m^3}\), \(\nu=1.5\times10^{-5}\,\mathrm{m^2/s}\) |
| \(\mathrm{Re}_H\) | ≈ \(7.68\times10^5\) |
| Turbulence (production) | **LES / `kOmegaSSTIDDES`** |
| Near-field solver | Incompressible `pimpleFoam` |
| Far-field | Compact **Curle** (Python) or **FW-H Farassat 1A** (`libAcoustics`) |
| Observers | 1 m, 3 m, 5 m aft of base + lateral (±y) |
| \(f_{\max}\) / sampling | 2.5 kHz / **50 kHz** (`writeInterval 2e-5`) |

Low Mach justifies an **incompressible** near-field CFD with an acoustic analogy for propagation (quadrupoles weak; loading/dipole noise dominates for solid surfaces).

## Four-stage workflow

```
[Mesh CAA] → [1 RANS] → [2 IDDES purge] → [3 CAA acquire] → [4 SPL]
```

### Stage 1 — Steady RANS (`system/stages/rans`)

- `simpleFoam` + `kOmegaSST`
- Builds attached/slant mean topology and provides \(k,\omega\) for IDDES
- ~500 iterations; force-coeff monitoring only

### Stage 2 — Transient purge (`system/stages/lesInit`)

- Switch to `pimpleFoam` + `kOmegaSSTIDDES`
- Schemes: **`backward`** (BDF2) + **`Gauss LUST`** convection (low dissipation)
- PIMPLE: 4 outer, 2 PISO, `maxCo 0.9`
- Run ≈ 0.5 s (~20 convective times \(L/U_\infty\)) **without** 50 kHz I/O

### Stage 3 — Production CAA (`system/stages/caa`)

- Same numerics/turbulence as Stage 2 (frozen)
- Fixed \(\Delta t=2\times10^{-5}\,\mathrm{s}\) (uniform acoustic clock, \(Co\ll1\))
- Function objects:
  - `acousticProbes` — field pressure at microphones
  - `acousticSurfaceSampling` — body surface \(p\) for Curle/FW-H
  - optional `#include "acousticFWH"` if `libAcoustics.so` is available
  - `fieldAverage` for \(\overline{U}\), \(u'u'\) validation

### Stage 4 — Spectra (`scripts/caa/compute_spl.py`)

1. Read probe histories (kinematic \(p\))
2. \(p_{\mathrm{Pa}}=\rho_\infty\,p\)
3. Welch PSD (Hann, 50% overlap)
4. Narrow-band SPL + **1/3-octave** aggregation to \(f_{\max}\)
5. Optional compact Curle from surface dumps

```sh
pip install -r scripts/caa/requirements-caa.txt
python3 scripts/caa/compute_spl.py --demo          # smoke test
python3 scripts/caa/compute_spl.py                 # after Stage 3
```

## Numerical choices (why)

| Choice | Rationale |
| --- | --- |
| IDDES over pure WALE | Affordable \(y^+\) hybrid; resolves slant/wake LES content that seeds noise |
| LUST vs pure linear | Central-biased with enough upwind to survive industrial meshes |
| BDF2 vs Crank–Nicolson | Avoids CN odd-even ringing in pressure that pollutes spectra |
| Fixed \(\Delta t\) in Stage 3 | Welch / FW-H assume uniform sampling |
| Incompressible + analogy | Ma≈0.12; full DDES/`rhoPimpleFoam` CAA is far costlier for same dipole physics |

## Directory map

```
system/
  stages/{rans,lesInit,caa}/   # controlDict, fvSchemes, fvSolution, turbulenceProperties
  acousticProbes               # microphone probes
  acousticSurfaceSampling      # body surface p @ 50 kHz
  acousticFWH                  # optional libAcoustics FW-H
  snappyHexMeshDict.caa        # acoustic mesh
  blockMeshDict.caa
scripts/caa/
  Allrun.caa / stage*.sh / activate_*.sh
  compute_spl.py
docs/caa/
  MESH_STRATEGY.md  METHODOLOGY.md  TROUBLESHOOTING.md
```

## Quick start

```sh
# Full pipeline (HPC recommended for CAA mesh)
./scripts/caa/Allrun.caa

# Or step-by-step
./scripts/caa/activate_mesh.sh caa && ./buildMesh
./scripts/caa/stage1_rans.sh
./scripts/caa/stage2_lesInit.sh
./scripts/caa/stage3_caa.sh
python3 scripts/caa/compute_spl.py --out-dir Reports/caa
```

Keep the original RANS validation path (`./Allrun`) unchanged for Cd/Cl checks.
