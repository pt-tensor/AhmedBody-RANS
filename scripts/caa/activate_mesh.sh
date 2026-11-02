#!/bin/sh
#------------------------------------------------------------------------------
# Switch between baseline RANS mesh dicts and CAA acoustic mesh overlays.
# Usage: ./scripts/caa/activate_mesh.sh <baseline|caa>
# Does NOT run the mesher — call ./buildMesh afterwards.
#------------------------------------------------------------------------------
cd "${0%/*}/../.." || exit 1

mode="$1"
case "$mode" in
baseline)
    if [ -f system/blockMeshDict.baseline ]
    then
        cp -f system/blockMeshDict.baseline system/blockMeshDict
        cp -f system/snappyHexMeshDict.baseline system/snappyHexMeshDict
    else
        echo "baseline snapshots missing — current dicts assumed baseline"
    fi
    echo "Mesh mode: baseline (RANS validation mesh)"
    ;;
caa)
    # Snapshot baseline once so we can restore later
    if [ ! -f system/blockMeshDict.baseline ]
    then
        cp -f system/blockMeshDict system/blockMeshDict.baseline
        cp -f system/snappyHexMeshDict system/snappyHexMeshDict.baseline
        echo "Saved baseline mesh dicts (*.baseline)"
    fi
    cp -f system/blockMeshDict.caa system/blockMeshDict
    cp -f system/snappyHexMeshDict.caa system/snappyHexMeshDict
    echo "Mesh mode: CAA (acoustic source resolution, y+≈1 layers)"
    ;;
*)
    echo "Usage: $0 <baseline|caa>"
    exit 1
    ;;
esac

#------------------------------------------------------------------------------
