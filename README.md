# Ahmed Bluff Body — RANS Validation + Hybrid CAA

Author: Caesar Wiratama

OpenFOAM ESI **v2312 / v2406** (syntax compatible with **v2206**) case for the **25° Ahmed body**.

| | RANS baseline | Hybrid CAA |
|--|--|--|
| **case_id** | 1-A | 1-A-CAA |
| **Decklid angle** | 25° | 25° |
| **Solver** | `simpleFoam` | `simpleFoam` → `pimpleFoam` |
| **Turbulence** | RAS `kOmegaSST` | LES `kOmegaSSTIDDES` |
| **Inlet U** | 40 m/s | 40 m/s (Ma ≈ 0.117) |
| **Acoustics** | — | Probes + surface \(p\) @ 50 kHz; Curle / optional FW-H |
| **\(f_{\max}\)** | — | 2.5 kHz |
| **Reference Cd / Cl (exp)** | 0.299 / 0.345 | time-averaged vs same |

## RANS validation (original)

```sh
./Allclean      # wipe mesh + results
./buildMesh     # surfaceFeatureExtract → snappyHexMesh → 0/
./Run           # decompose → potentialFoam → simpleFoam → reconstruct
```

Or `./Allrun`. Force coeffs: `postProcessing/forceCoeffs1/`. Plots:

```sh
python3 Reports/scripts/plot_force_coeffs.py
```

## Hybrid CAA (LES/IDDES + acoustic analogy)

Full documentation:

- [docs/caa/METHODOLOGY.md](docs/caa/METHODOLOGY.md) — stages, schemes, FW-H
- [docs/caa/MESH_STRATEGY.md](docs/caa/MESH_STRATEGY.md) — \(y^+\approx1\), cells/λ
- [docs/caa/TROUBLESHOOTING.md](docs/caa/TROUBLESHOOTING.md) — reflections, dissipation, init

```sh
# End-to-end (HPC: CAA mesh is O(10M–60M) cells)
./scripts/caa/Allrun.caa

# Manual stages
./scripts/caa/activate_mesh.sh caa && ./buildMesh
./scripts/caa/stage1_rans.sh      # steady RANS init
./scripts/caa/stage2_lesInit.sh   # IDDES purge ~0.5 s
./scripts/caa/stage3_caa.sh       # production + 50 kHz sampling
pip install -r scripts/caa/requirements-caa.txt
python3 scripts/caa/compute_spl.py --out-dir Reports/caa
```

Smoke-test the SPL pipeline without CFD:

```sh
python3 scripts/caa/compute_spl.py --demo --out-dir Reports/caa
```

### Stage dictionaries

| Stage | Path | Application |
| --- | --- | --- |
| 1 RANS | `system/stages/rans/` | `simpleFoam` |
| 2 Purge | `system/stages/lesInit/` | `pimpleFoam` + IDDES |
| 3 CAA | `system/stages/caa/` | `pimpleFoam` + probes/surfaces |

Activate with `./scripts/caa/activate_stage.sh <rans|lesInit|caa>`.

### Observers

Microphones at ~1, 3, 5 m aft of the base and lateral (±y), defined in `system/acousticProbes`. Optional FW-H: `system/acousticFWH` (requires `libAcoustics.so`).

## Geometry & BCs

- STL: `constant/triSurface/ahmed_25deg_m.stl`
- Domain: \(x\in[-5,15]\), \(y\in[-4,4]\), \(z\in[0,8]\) m
- Walls: `ahmed_body` (no-slip) + `lowerWall` (moving ground)
- Slip: `upperWall`, `frontAndBack`
- Initial fields: `0.orig/`

Default decomposition: **8** ranks (`system/decomposeParDict`). Increase for CAA meshes.
