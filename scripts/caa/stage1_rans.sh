#!/bin/sh
#------------------------------------------------------------------------------
# STAGE 1 — Steady RANS initialisation (simpleFoam)
# Prerequisite: mesh present (./scripts/caa/activate_mesh.sh caa && ./buildMesh)
#------------------------------------------------------------------------------
cd "${0%/*}/../.." || exit 1
. ${WM_PROJECT_DIR:?}/bin/tools/RunFunctions

set -e

./scripts/caa/activate_stage.sh rans

if [ ! -f constant/polyMesh/points ]
then
    echo "Error: no mesh. Run: ./scripts/caa/activate_mesh.sh caa && ./buildMesh"
    exit 1
fi

if [ ! -f 0/U ]
then
    restore0Dir
fi

rm -rf processor*
runApplication -o decomposePar

nProcs=$(getNumberOfProcessors)
runParallel -o potentialFoam -writephi

echo "STAGE 1: simpleFoam ($nProcs ranks)"
mpirun --oversubscribe -n "$nProcs" simpleFoam -parallel

runApplication -o reconstructPar -latestTime

echo "STAGE 1 complete. Latest time ready for IDDES hand-off."

#------------------------------------------------------------------------------
