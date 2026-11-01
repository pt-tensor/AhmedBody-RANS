# Mesh Strategy — Ahmed 25° Hybrid CAA

**Target OpenFOAM:** ESI **v2312 / v2406** (syntax compatible with **v2206**).

## Design targets

| Quantity | Value | Implication |
| --- | --- | --- |
| \(f_{\max}\) | 2500 Hz | \(\lambda_{\min}=c_0/f_{\max}\approx0.137\,\mathrm{m}\) |
| Cells / wavelength (source) | 15–20 | \(\Delta x_{\mathrm{src}}\lesssim9\,\mathrm{mm}\) |
| \(y^+\) (body) | ≈ 1 | \(y_1\approx1\times10^{-5}\,\mathrm{m}\) |
| \(U_\infty\), \(H\), \(\nu\) | 40 m/s, 0.288 m, \(1.5\times10^{-5}\) | \(\mathrm{Re}_H\approx7.68\times10^5\) |

## Background (`blockMeshDict.caa`)

- Domain unchanged: \(x\in[-5,15]\), \(y\in[-4,4]\), \(z\in[0,8]\) m.
- Resolution raised from `(24 10 10)` → **`(40 20 20)`** so snappy levels land at the acoustic \(\Delta x\) target.
- Optional (advanced): stretch outlet to \(x=25\) m and add a sponge (`fvOptions` explicit damping) to kill spurious reflections.

## Castellated refinement (`snappyHexMeshDict.caa`)

| Region | Purpose | Level (≈ cell size) |
| --- | --- | --- |
| Body surface | Curle/FW-H loading surface | (6–7) ≈ 4–8 mm |
| Feature edges | Slant / C-pillar shedding seeds | 8 ≈ 2 mm |
| `refinementBox_slant` | Separation bubble + C-pillar | 6 |
| `refinementBox_base` | Base wake shear layers | 6 |
| Near / mid / far wake boxes | Cascade size transition | 5 → 4 → 3 |
| Body distance levels | Protect near-field acoustics | 7 / 6 / 5 |

`nCellsBetweenLevels 4` softens hanging-node jumps that otherwise radiate numerical noise into pressure probes.

## Prism layers (absolute sizes)

```
relativeSizes false;
firstLayerThickness 2.0e-5;   // → y+ ~ 1 at U∞=40
expansionRatio 1.2;
nSurfaceLayers 18;            // ahmed_body
```

After meshing, verify:

```sh
checkMesh -constant
# In paraFoam / yPlus functionObject after a short RANS:
# mean y+ on ahmed_bodyGroup should be O(1)
```

## Expected size

CAA mesh is **much** larger than the RANS validation medium mesh (~0.7 M). Plan for **O(20–60 M)** cells depending on wake box extent; adjust `maxGlobalCells` and box bounds for available HPC.

## Activate

```sh
./scripts/caa/activate_mesh.sh caa
./buildMesh
# restore RANS validation mesh dicts:
./scripts/caa/activate_mesh.sh baseline
```
