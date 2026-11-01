# CAA Troubleshooting — Ahmed Body

## 1. Spurious numerical wave reflections at boundaries

**Symptoms:** Periodic spikes in probe SPL, grid-tone peaks unrelated to St shedding, sensitivity to domain size.

**Mitigations:**

- Keep a long outlet (current \(x=15\); prefer \(x\geq20\)–\(25\) for CAA).
- Prefer `advective` / `inletOutlet` on `U` at outlet; avoid abrupt `fixedValue` on velocity.
- Pressure outlet: `fixedValue` is acceptable for incompressible if the domain is large; for stubborn reflections add a **sponge zone** via `fvOptions` (`explicitPorositySource` / coded damping on \(U'\) near outlet).
- Do **not** place microphones near the outlet patch (observers at 1–5 m aft of base are fine inside this domain).
- Slip sides (`frontAndBack`, `upperWall`) reflect acoustic energy in incompressible runs — treat in-domain probe SPL as comparative, or use FW-H from the **body surface** (preferred) so boundaries never enter the acoustic integral.

## 2. High grid dissipation of acoustic sources

**Symptoms:** OASPL too low vs literature; spectra roll off well below 2.5 kHz; wake structures look overly smooth.

**Mitigations:**

- Confirm source-region \(\Delta x\lesssim9\,\mathrm{mm}\) (snappy levels 6–7 active in slant/base boxes).
- Use **`Gauss LUST`** (or pure `linear` if stable) — never `upwind` / `linearUpwind` for production CAA convection.
- Keep `maxCo < 1` (Stage 2) and fixed \(\Delta t=2\times10^{-5}\) (Stage 3).
- Avoid excessive `cellLimited` on `grad(U)` in Stage 3.
- Ensure IDDES is in LES mode in the wake: inspect \(l_\mathrm{LES}/l_\mathrm{RANS}\) or \(\nu_\mathrm{sgs}/\nu\) — if RANS mode bleeds into shear layers, tighten wake refinement.

## 3. Convergence instability at transient initiation (RANS → IDDES)

**Symptoms:** Immediate floating-point exception, exploding Courant, diverging `p` residual in first 100 steps.

**Mitigations:**

- Always start IDDES from a **converged RANS** field (Stage 1), not from potential flow alone.
- Stage 2: `nOuterCorrectors 4`, under-relax `U/p` ~0.7, `adjustTimeStep yes` with `maxCo 0.9`.
- Temporarily use `Gauss linearUpwindV grad(U)` for the first 0.05 s, then switch back to LUST (or keep LUST with smaller \(\Delta t\)).
- Check mesh quality: non-orthogonality < 70°, no negative volumes after layers (`checkMesh`).
- If `omega` spikes at walls, confirm `omegaWallFunction` + reasonable `turbulentOmega` inlet.

## 4. Acoustic sampling / I/O bottlenecks

**Symptoms:** Wall-clock dominated by writing; disk full; uneven `writeInterval`.

**Mitigations:**

- Sample acoustics **only in Stage 3**; Stage 2 should omit probes/surfaces.
- Prefer `surfaceFormat raw` over VTK for long surface histories.
- Write volume fields sparsely (`writeInterval 0.05`); keep probe rate at 50 kHz.
- Parallel filesystem: put `postProcessing/` on scratch; rsync raw probes for Python offline.

## 5. `libAcoustics` / FW-H library missing

**Symptoms:** `FOAM FATAL ERROR: Unknown function type FfowcsWilliamsHawkings`.

**Mitigations:**

- Keep `#include "acousticFWH"` **commented** (default).
- Use `acousticSurfaceSampling` + `scripts/caa/compute_spl.py` (probes + optional Curle).
- To enable FW-H: build [unicfdlab/libAcoustics](https://github.com/unicfdlab/libAcoustics) against your ESI version, install `libAcoustics.so`, then uncomment the include.

## 6. Welch spectra look noisy or unresolved

**Symptoms:** Random SPL scatter; no clear St peak; \(\Delta f\) too coarse.

**Mitigations:**

- Acquire ≥ 0.2–0.5 s of **stationary** Stage-3 data after purge.
- Increase `nperseg` (script auto-picks from record length); more averages → smoother PSD.
- Confirm actual \(f_s\) ≈ 50 kHz (`summary.json`); if adjustable time stepping leaked into Stage 3, re-run with `adjustTimeStep no`.
- Convert kinematic pressure with \(\rho=1.225\) before SPL (script default).

## 7. Force coefficients drift after IDDES switch

Expected: instantaneous \(C_d,C_l\) fluctuate; compare **time averages** over Stage 3 to RANS / experiment (Cd≈0.30, Cl≈0.35). Large mean drift (>10%) → mesh too coarse in slant or IDDES not resolving C-pillar vortices.
