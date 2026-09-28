#!/bin/bash

set -e

# ============================================================
# OMNeT++ / INET environment
# ============================================================

OMNET_ROOT="$HOME/sim/omnetpp/omnetpp-6.0.3"
export INET_ROOT="/home/gui/sim/inet"

# setenv is normally sourced from the OMNeT++ directory
pushd "$OMNET_ROOT" > /dev/null
. setenv
popd > /dev/null

# Optional sanity checks
if ! command -v opp_run > /dev/null 2>&1; then
    echo "ERROR: opp_run not found"
    exit 1
fi

if [ ! -d "$INET_ROOT" ]; then
    echo "ERROR: INET_ROOT does not exist: $INET_ROOT"
    exit 1
fi


# ============================================================
# Experiment
# ============================================================

RUN_DIR="$(pwd)"

SCRIPT_NAME="$(basename "$0")"
SCRIPT_BASE="${SCRIPT_NAME%.*}"

OUTPUT_DIR="$RUN_DIR/$SCRIPT_BASE"
OUTPUT_PLOT="$OUTPUT_DIR/$SCRIPT_BASE.png"
OUTPUT_PLOT_SURROGATE="$RUN_DIR/${SCRIPT_BASE}_surrogate/$SCRIPT_BASE.png"
OUTPUT_PLOT_HYBRID="$RUN_DIR/${SCRIPT_BASE}_hybrid/$SCRIPT_BASE.png"


echo "=== Building project ==="

cd ../..

cmake -S  . -B build
cmake --build build --clean-first -j

cd build

echo "=== Running optimizer surrogate ==="

./surrogated-assisted-optimizer naive 3_relays/high-high/1 0 400
./surrogated-assisted-optimizer naive 3_relays/high-high/2 0 400
./surrogated-assisted-optimizer naive 3_relays/high-high/3 0 400
./surrogated-assisted-optimizer naive 3_relays/high-high/4 0 400
./surrogated-assisted-optimizer naive 3_relays/high-high/5 0 400
./surrogated-assisted-optimizer naive 3_relays/high-high/6 0 400
./surrogated-assisted-optimizer naive 3_relays/high-high/7 0 400
./surrogated-assisted-optimizer naive 3_relays/high-high/8 0 400
./surrogated-assisted-optimizer naive 3_relays/high-high/9 0 400
./surrogated-assisted-optimizer naive 3_relays/high-high/10 0 400
./surrogated-assisted-optimizer naive 3_relays/high-high/11 0 400
./surrogated-assisted-optimizer naive 3_relays/high-high/12 0 400
./surrogated-assisted-optimizer naive 3_relays/high-high/13 0 400
./surrogated-assisted-optimizer naive 3_relays/high-high/14 0 400
./surrogated-assisted-optimizer naive 3_relays/high-high/15 0 400
./surrogated-assisted-optimizer naive 3_relays/high-high/16 0 400
./surrogated-assisted-optimizer naive 3_relays/high-high/17 0 400
./surrogated-assisted-optimizer naive 3_relays/high-high/18 0 400
./surrogated-assisted-optimizer naive 3_relays/high-high/19 0 400
./surrogated-assisted-optimizer naive 3_relays/high-high/20 0 400
./surrogated-assisted-optimizer naive 3_relays/high-high/21 0 400
./surrogated-assisted-optimizer naive 3_relays/high-high/22 0 400
./surrogated-assisted-optimizer naive 3_relays/high-high/23 0 400
./surrogated-assisted-optimizer naive 3_relays/high-high/24 0 400
./surrogated-assisted-optimizer naive 3_relays/high-high/25 0 400

echo

echo "=== Optimizer with surrgate finished ==="


