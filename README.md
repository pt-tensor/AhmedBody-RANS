# Ahmed Bluff Body

Author: Caesar Wiratama

Steady RANS validation of the **25° Ahmed body**,

| | |
|--|--|
| **case_id** | 1-A |
| **Decklid angle** | 25° |
| **Solver** | `simpleFoam` |
| **Turbulence** | RAS — `kOmegaSST` |
| **Inlet U** | 40 m/s |
| **Reference Cd / Cl (exp)** | 0.299 / 0.345 |
| **Prior OF-7 Cd / Cl** | 0.299 / 0.339 |
| **Mesh (1-A)** | ~8.25 M cells |

## Run

```sh
./Allclean      # wipe mesh + results
./buildMesh     # surfaceFeatureExtract → snappyHexMesh → 0/
./Run           # decompose → potentialFoam → simpleFoam → reconstruct
```

Or all-in-one: `./Allrun` (= `./buildMesh` then `./Run`).

To re-solve without remeshing:

```sh
./cleanResults
./Run
```

Default decomposition: **8** ranks (`system/decomposeParDict`, hierarchical `(4 2 1)`). Adjust
`numberOfSubdomains` / `coeffs.n` if needed.

After the run, force coefficients are in
`postProcessing/forceCoeffs1/<time>/coefficient.dat`. Average the last
50 iterations for Cd / Cl (same post-process as the original case).

Refresh plots:

```sh
python3 Reports/scripts/plot_force_coeffs.py
```

Outputs: `Reports/figures/Cd_vs_iteration.svg`, `Reports/figures/Cl_vs_iteration.svg`
(exp refs Cd=0.299, Cl=0.345).

## Geometry & BCs

- STL: `constant/triSurface/ahmed_25deg_m.stl`
- Domain: `x ∈ [-5, 15]`, `y ∈ [-4, 4]`, `z ∈ [0, 8]` m
- Walls: `ahmed_body` (no-slip) + `lowerWall` (moving ground, U = freestream)
- Slip: `upperWall`, `frontAndBack`
- Initial fields live in `0.orig/` and are restored onto processors after meshing

