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

#./surrogated-assisted-optimizer pso 8 0 4 0.8 1.2 1.8

echo

echo "=== Optimizer with simulation finished ==="

echo "=== Plotting simulation nodes ==="

#cd "$RUN_DIR"

#python3 ../plot.py "$OUTPUT_PLOT"

#echo "Plot saved to: $OUTPUT_PLOT"

echo "=== Starting surrogate server ==="

cd "$RUN_DIR"

python3 ../../surrogate_model/inferenceService.py &

SERVER_PID=$!

# Make sure the server is killed even if the script fails
trap 'kill "$SERVER_PID" 2>/dev/null || true' EXIT

# Give Python time to load the RF and open the socket
sleep 2

# Check that the process is still alive
if ! kill -0 "$SERVER_PID" 2>/dev/null; then
    echo "ERROR: surrogate server failed to start"
    cat "$RUN_DIR/${SCRIPT_BASE}_surrogate/server.log"
    exit 1
fi

echo "Surrogate server running with PID $SERVER_PID"

cd ../../build

echo "=== Running optimizer with surrogate ==="

./surrogated-assisted-optimizer pso 8 1 4 0.8 1.2 1.8

echo

echo "=== Optimizer with surrogate finished ==="

echo "=== Stopping surrogate server ==="

kill "$SERVER_PID"
wait "$SERVER_PID" 2>/dev/null || true

trap - EXIT


echo "=== Plotting nodes ==="

cd "$RUN_DIR"

python3 ../plot.py "$OUTPUT_PLOT_SURROGATE"

echo "Plot saved to: $OUTPUT_PLOT_SURROGATE"
