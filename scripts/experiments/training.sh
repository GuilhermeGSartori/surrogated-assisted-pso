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

echo "=== Generating training dataset 1 ==="

./surrogated-assisted-optimizer training training_1

echo

echo "=== Dataset generation finished ==="

cd "$RUN_DIR"

echo "=== Training Random Forest ==="

source ../../.venv/bin/activate

python3 ../../surrogate_model/trainer.py rf_4r_c1_hy1

echo

echo "=== Random Forest training finished ==="

cd ../..
cd build

echo "=== Generating training dataset 2 ==="

#./surrogated-assisted-optimizer training training_2

echo

echo "=== Dataset generation finished ==="

cd "$RUN_DIR"

echo "=== Training Random Forest ==="

echo "=== Change nodes.csv to the correct number of clusters, comment the training_1 (python and optimizer) and run this again"
echo "=== And after, change the trainer.py hyperparameters and train with both pythons withoyt any optimizer and chaning the name of the model"

#python3 ../../surrogate_model/trainer.py rf_4r_c2_hy1

echo "=== Random Forest training finished ==="