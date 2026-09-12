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

mkdir -p "$RUN_DIR/${SCRIPT_BASE}_surrogate"
mkdir -p "$OUTPUT_DIR"


echo "=== Building project ==="

cd ../..

cmake -S  . -B build
cmake --build build --clean-first -j

cd build

echo

echo "=== Running optimizer with simulation ==="

./surrogated-assisted-optimizer pso 10 0 4 0.8 1.2 1.8

echo

echo "=== Optimizer with simulation finished ==="

echo "=== Plotting simulation nodes ==="

cd "$RUN_DIR"

python3 ../plot.py "$OUTPUT_PLOT"

echo "Plot saved to: $OUTPUT_PLOT"
