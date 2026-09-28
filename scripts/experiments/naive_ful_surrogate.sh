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

echo

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

echo "=== Running optimizer surrogate ==="

#./surrogated-assisted-optimizer naive 3_relays/high-high/1 1 400
#./surrogated-assisted-optimizer naive 3_relays/high-high/2 1 400
#./surrogated-assisted-optimizer naive 3_relays/high-high/3 1 400
#./surrogated-assisted-optimizer naive 3_relays/high-high/4 1 400
#./surrogated-assisted-optimizer naive 3_relays/high-high/5 1 400
#./surrogated-assisted-optimizer naive 3_relays/high-high/6 1 400
#./surrogated-assisted-optimizer naive 3_relays/high-high/7 1 400
#./surrogated-assisted-optimizer naive 3_relays/high-high/8 1 400
#./surrogated-assisted-optimizer naive 3_relays/high-high/9 1 400
#./surrogated-assisted-optimizer naive 3_relays/high-high/10 1 400
#./surrogated-assisted-optimizer naive 3_relays/high-high/11 1 400
#./surrogated-assisted-optimizer naive 3_relays/high-high/12 1 400
./surrogated-assisted-optimizer naive 3_relays/high-high/13 1 400
./surrogated-assisted-optimizer naive 3_relays/high-high/14 1 400
./surrogated-assisted-optimizer naive 3_relays/high-high/15 1 400
./surrogated-assisted-optimizer naive 3_relays/high-high/16 1 400
./surrogated-assisted-optimizer naive 3_relays/high-high/17 1 400
./surrogated-assisted-optimizer naive 3_relays/high-high/18 1 400
./surrogated-assisted-optimizer naive 3_relays/high-high/19 1 400
./surrogated-assisted-optimizer naive 3_relays/high-high/20 1 400
./surrogated-assisted-optimizer naive 3_relays/high-high/21 1 400
./surrogated-assisted-optimizer naive 3_relays/high-high/22 1 400
./surrogated-assisted-optimizer naive 3_relays/high-high/23 1 400
./surrogated-assisted-optimizer naive 3_relays/high-high/24 1 400
./surrogated-assisted-optimizer naive 3_relays/high-high/25 1 400

echo

echo "=== Optimizer with surrgate finished ==="

kill "$SERVER_PID"
wait "$SERVER_PID" 2>/dev/null || true

trap - EXIT


