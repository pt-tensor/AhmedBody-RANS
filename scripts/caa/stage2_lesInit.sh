#!/bin/sh
#------------------------------------------------------------------------------
# STAGE 2 — IDDES purge of numerical transients (pimpleFoam, ~0.5 s)
# Prerequisite: Stage 1 finished (latestTime RANS fields).
#------------------------------------------------------------------------------
cd "${0%/*}/../.." || exit 1
. ${WM_PROJECT_DIR:?}/bin/tools/RunFunctions

set -e

./scripts/caa/activate_stage.sh lesInit

# Map / keep RANS fields; IDDES reuses k, omega, nut, U, p
rm -rf processor*
runApplication -o decomposePar

nProcs=$(getNumberOfProcessors)

echo "STAGE 2: pimpleFoam IDDES purge ($nProcs ranks)"
mpirun --oversubscribe -n "$nProcs" pimpleFoam -parallel

runApplication -o reconstructPar -latestTime

echo "STAGE 2 complete. Proceed to Stage 3 production CAA."

#------------------------------------------------------------------------------
