#!/bin/sh
#------------------------------------------------------------------------------
# STAGE 3 — Production CAA acquisition (50 kHz probes + surface pressure)
# Prerequisite: Stage 2 finished. Continues from latestTime.
#------------------------------------------------------------------------------
cd "${0%/*}/../.." || exit 1
. ${WM_PROJECT_DIR:?}/bin/tools/RunFunctions

set -e

./scripts/caa/activate_stage.sh caa

rm -rf processor*
runApplication -o decomposePar

nProcs=$(getNumberOfProcessors)

echo "STAGE 3: pimpleFoam CAA production ($nProcs ranks)"
echo "  Acoustic probes + surface sampling at 50 kHz (Δt write = 2e-5 s)"
mpirun --oversubscribe -n "$nProcs" pimpleFoam -parallel

runApplication -o reconstructPar -latestTime

echo "STAGE 3 complete."
echo "  Probes:   postProcessing/acousticProbes/"
echo "  Surfaces: postProcessing/acousticSurfaceSampling/"
echo "  SPL:      python3 scripts/caa/compute_spl.py"

#------------------------------------------------------------------------------
