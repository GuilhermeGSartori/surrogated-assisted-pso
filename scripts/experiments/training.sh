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

echo "=== Building project ==="

cd ../..

cmake -S  . -B build
cmake --build build --clean-first -j

cd build

echo

echo "=== Generating training dataset ==="

#./surrogated-assisted-optimizer training training_1

echo

echo "=== Dataset generation finished ==="

cd "$RUN_DIR"

echo "=== Training Random Forest ==="

source ../../.venv/bin/activate

# To train, must change nodes.csv for cluster and trainer.py for hyperparameters
# To use, must change scenarios.csv to match the number of clusters and the used model name!
python3 ../../surrogate_model/trainer.py rf_4r_c1_hy1
#python3 ../../surrogate_model/trainer.py rf_4r_c2_hy1
#python3 ../../surrogate_model/trainer.py rf_4r_c3_hy1
#python3 ../../surrogate_model/trainer.py rf_4r_c1_hy2
#python3 ../../surrogate_model/trainer.py rf_4r_c2_hy2
#python3 ../../surrogate_model/trainer.py rf_4r_c3_hy3
#python3 ../../surrogate_model/trainer.py rf_4r_c1_hy3
#python3 ../../surrogate_model/trainer.py rf_4r_c2_hy3
#python3 ../../surrogate_model/trainer.py rf_4r_c3_hy3
#
echo

echo "=== Random Forest training finished ==="
