#!/bin/sh
#------------------------------------------------------------------------------
# Activate a CAA workflow stage by copying stage dictionaries into place.
# Usage: ./scripts/caa/activate_stage.sh <rans|lesInit|caa>
#------------------------------------------------------------------------------
cd "${0%/*}/../.." || exit 1

stage="$1"
if [ -z "$stage" ]
then
    echo "Usage: $0 <rans|lesInit|caa>"
    exit 1
fi

srcdir="system/stages/$stage"
if [ ! -d "$srcdir" ]
then
    echo "Error: unknown stage '$stage' (expected system/stages/$stage)"
    exit 1
fi

cp -f "$srcdir/controlDict"   system/controlDict
cp -f "$srcdir/fvSchemes"     system/fvSchemes
cp -f "$srcdir/fvSolution"    system/fvSolution
cp -f "$srcdir/turbulenceProperties" constant/turbulenceProperties

echo "Activated stage: $stage"
echo "  application = $(sed -n 's/^application[[:space:]]*//p' system/controlDict | tr -d ';')"
echo "  turbulence  = constant/turbulenceProperties"

#------------------------------------------------------------------------------
