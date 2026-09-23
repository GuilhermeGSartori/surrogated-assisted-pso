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
OUTPUT_DIR_NAIVE="$RUN_DIR/${SCRIPT_BASE}_naive"

mkdir -p "$OUTPUT_DIR"
mkdir -p "$OUTPUT_DIR_NAIVE"


echo "=== Building project ==="

cd ../..

cmake -S  . -B build
cmake --build build --clean-first -j

##################################

cd build

./surrogated-assisted-optimizer pso 4_relays/high-high/1 0 20 0.8 1.7 1.3

cd "$RUN_DIR"

source ../../.venv/bin/activate

OUTPUT_PLOT="$OUTPUT_DIR/4_relays-1.png"

python3 ../plot.py "$OUTPUT_PLOT"

cd ../..
cd build

./surrogated-assisted-optimizer naive 4_relays/high-high/1 0 400

cd "$RUN_DIR"

OUTPUT_PLOT_NAIVE="$OUTPUT_DIR_NAIVE/4_relays-1.png"

python3 ../plot.py "$OUTPUT_PLOT_NAIVE"

#######################

cd ../..
cd build

./surrogated-assisted-optimizer pso 4_relays/high-high/2 0 20 0.8 1.7 1.3
cd "$RUN_DIR"

OUTPUT_PLOT="$OUTPUT_DIR/4_relays-2.png"

python3 ../plot.py "$OUTPUT_PLOT"

cd ../..
cd build

./surrogated-assisted-optimizer naive 4_relays/high-high/2 0 400

cd "$RUN_DIR"

OUTPUT_PLOT_NAIVE="$OUTPUT_DIR_NAIVE/4_relays-2.png"

python3 ../plot.py "$OUTPUT_PLOT_NAIVE"

##################

cd ../..
cd build

./surrogated-assisted-optimizer pso 4_relays/high-high/3 0 20 0.8 1.7 1.3
cd "$RUN_DIR"

OUTPUT_PLOT="$OUTPUT_DIR/4_relays-3.png"

python3 ../plot.py "$OUTPUT_PLOT"

cd ../..
cd build

./surrogated-assisted-optimizer naive 4_relays/high-high/3 0 400

cd "$RUN_DIR"

OUTPUT_PLOT_NAIVE="$OUTPUT_DIR_NAIVE/4_relays-3.png"

python3 ../plot.py "$OUTPUT_PLOT_NAIVE"

######################

cd ../..
cd build

./surrogated-assisted-optimizer pso 4_relays/high-high/4 0 20 0.8 1.7 1.3
cd "$RUN_DIR"

OUTPUT_PLOT="$OUTPUT_DIR/4_relays-4.png"

python3 ../plot.py "$OUTPUT_PLOT"

cd ../..
cd build

./surrogated-assisted-optimizer naive 4_relays/high-high/4 0 400

cd "$RUN_DIR"

OUTPUT_PLOT_NAIVE="$OUTPUT_DIR_NAIVE/4_relays-4.png"

python3 ../plot.py "$OUTPUT_PLOT_NAIVE"


######################

cd ../..
cd build

./surrogated-assisted-optimizer pso 4_relays/high-high/5 0 20 0.8 1.7 1.3
cd "$RUN_DIR"

OUTPUT_PLOT="$OUTPUT_DIR/4_relays-5.png"

python3 ../plot.py "$OUTPUT_PLOT"

cd ../..
cd build

./surrogated-assisted-optimizer naive 4_relays/high-high/5 0 400

cd "$RUN_DIR"

OUTPUT_PLOT_NAIVE="$OUTPUT_DIR_NAIVE/4_relays-5.png"

python3 ../plot.py "$OUTPUT_PLOT_NAIVE"

#############################

cd ../..
cd build

./surrogated-assisted-optimizer pso 4_relays/high-high/6 0 20 0.8 1.7 1.3
cd "$RUN_DIR"

OUTPUT_PLOT="$OUTPUT_DIR/4_relays-6.png"

python3 ../plot.py "$OUTPUT_PLOT"

cd ../..
cd build

./surrogated-assisted-optimizer naive 4_relays/high-high/6 0 400

cd "$RUN_DIR"

OUTPUT_PLOT_NAIVE="$OUTPUT_DIR_NAIVE/4_relays-6.png"

python3 ../plot.py "$OUTPUT_PLOT_NAIVE"

##############################

cd ../..
cd build

./surrogated-assisted-optimizer pso 4_relays/high-high/7 0 20 0.8 1.7 1.3
cd "$RUN_DIR"

OUTPUT_PLOT="$OUTPUT_DIR/4_relays-7.png"

python3 ../plot.py "$OUTPUT_PLOT"

cd ../..
cd build

./surrogated-assisted-optimizer naive 4_relays/high-high/7 0 400

cd "$RUN_DIR"

OUTPUT_PLOT_NAIVE="$OUTPUT_DIR_NAIVE/4_relays-7.png"

python3 ../plot.py "$OUTPUT_PLOT_NAIVE"

#############################

cd ../..
cd build

./surrogated-assisted-optimizer pso 4_relays/high-high/8 0 20 0.8 1.7 1.3
cd "$RUN_DIR"

OUTPUT_PLOT="$OUTPUT_DIR/4_relays-8.png"

python3 ../plot.py "$OUTPUT_PLOT"

cd ../..
cd build

./surrogated-assisted-optimizer naive 4_relays/high-high/8 0 400

cd "$RUN_DIR"

OUTPUT_PLOT_NAIVE="$OUTPUT_DIR_NAIVE/4_relays-8.png"

python3 ../plot.py "$OUTPUT_PLOT_NAIVE"

#############################

cd ../..
cd build

./surrogated-assisted-optimizer pso 4_relays/high-high/9 0 20 0.8 1.7 1.3
cd "$RUN_DIR"

OUTPUT_PLOT="$OUTPUT_DIR/4_relays-9.png"

python3 ../plot.py "$OUTPUT_PLOT"

cd ../..
cd build

./surrogated-assisted-optimizer naive 4_relays/high-high/9 0 400

cd "$RUN_DIR"

OUTPUT_PLOT_NAIVE="$OUTPUT_DIR_NAIVE/4_relays-9.png"

python3 ../plot.py "$OUTPUT_PLOT_NAIVE"

#######################

cd ../..
cd build

./surrogated-assisted-optimizer pso 4_relays/high-high/10 0 20 0.8 1.7 1.3
cd "$RUN_DIR"

OUTPUT_PLOT="$OUTPUT_DIR/4_relays-10.png"

python3 ../plot.py "$OUTPUT_PLOT"

cd ../..
cd build

./surrogated-assisted-optimizer naive 4_relays/high-high/10 0 400

cd "$RUN_DIR"

OUTPUT_PLOT_NAIVE="$OUTPUT_DIR_NAIVE/4_relays-10.png"

python3 ../plot.py "$OUTPUT_PLOT_NAIVE"

#######################

cd ../..
cd build

./surrogated-assisted-optimizer pso 4_relays/high-high/11 0 20 0.8 1.7 1.3
cd "$RUN_DIR"

OUTPUT_PLOT="$OUTPUT_DIR/4_relays-11.png"

python3 ../plot.py "$OUTPUT_PLOT"

cd ../..
cd build

./surrogated-assisted-optimizer naive 4_relays/high-high/11 0 400

cd "$RUN_DIR"

OUTPUT_PLOT_NAIVE="$OUTPUT_DIR_NAIVE/4_relays-11.png"

python3 ../plot.py "$OUTPUT_PLOT_NAIVE"

#######################

cd ../..
cd build

./surrogated-assisted-optimizer pso 4_relays/high-high/12 0 20 0.8 1.7 1.3
cd "$RUN_DIR"

OUTPUT_PLOT="$OUTPUT_DIR/4_relays-12.png"

python3 ../plot.py "$OUTPUT_PLOT"

cd ../..
cd build

./surrogated-assisted-optimizer naive 4_relays/high-high/12 0 400

cd "$RUN_DIR"

OUTPUT_PLOT_NAIVE="$OUTPUT_DIR_NAIVE/4_relays-12.png"

python3 ../plot.py "$OUTPUT_PLOT_NAIVE"

#######################

cd ../..
cd build

./surrogated-assisted-optimizer pso 4_relays/high-mid/1 0 20 0.8 1.7 1.3
cd "$RUN_DIR"

OUTPUT_PLOT="$OUTPUT_DIR/4_relays-13.png"

python3 ../plot.py "$OUTPUT_PLOT"

cd ../..
cd build

./surrogated-assisted-optimizer naive 4_relays/high-mid/1 0 400

cd "$RUN_DIR"

OUTPUT_PLOT_NAIVE="$OUTPUT_DIR_NAIVE/4_relays-13.png"

python3 ../plot.py "$OUTPUT_PLOT_NAIVE"

#############################

cd ../..
cd build

./surrogated-assisted-optimizer pso 4_relays/high-mid/2 0 20 0.8 1.7 1.3
cd "$RUN_DIR"

OUTPUT_PLOT="$OUTPUT_DIR/4_relays-14.png"

python3 ../plot.py "$OUTPUT_PLOT"

cd ../..
cd build

./surrogated-assisted-optimizer naive 4_relays/high-mid/2 0 400

cd "$RUN_DIR"

OUTPUT_PLOT_NAIVE="$OUTPUT_DIR_NAIVE/4_relays-14.png"

python3 ../plot.py "$OUTPUT_PLOT_NAIVE"

##############################

cd ../..
cd build

./surrogated-assisted-optimizer pso 4_relays/high-mid/3 0 20 0.8 1.7 1.3
cd "$RUN_DIR"

OUTPUT_PLOT="$OUTPUT_DIR/4_relays-15.png"

python3 ../plot.py "$OUTPUT_PLOT"

cd ../..
cd build

./surrogated-assisted-optimizer naive 4_relays/high-mid/3 0 400

cd "$RUN_DIR"

OUTPUT_PLOT_NAIVE="$OUTPUT_DIR_NAIVE/4_relays-15.png"

python3 ../plot.py "$OUTPUT_PLOT_NAIVE"

#############################

cd ../..
cd build

./surrogated-assisted-optimizer pso 4_relays/high-mid/4 0 20 0.8 1.7 1.3
cd "$RUN_DIR"

OUTPUT_PLOT="$OUTPUT_DIR/4_relays-16.png"

python3 ../plot.py "$OUTPUT_PLOT"

cd ../..
cd build

./surrogated-assisted-optimizer naive 4_relays/high-mid/4 0 400

cd "$RUN_DIR"

OUTPUT_PLOT_NAIVE="$OUTPUT_DIR_NAIVE/4_relays-16.png"

python3 ../plot.py "$OUTPUT_PLOT_NAIVE"

#############################

cd ../..
cd build

./surrogated-assisted-optimizer pso 4_relays/high-mid/5 0 20 0.8 1.7 1.3
cd "$RUN_DIR"

OUTPUT_PLOT="$OUTPUT_DIR/4_relays-17.png"

python3 ../plot.py "$OUTPUT_PLOT"

cd ../..
cd build

./surrogated-assisted-optimizer naive 4_relays/high-mid/5 0 400

cd "$RUN_DIR"

OUTPUT_PLOT_NAIVE="$OUTPUT_DIR_NAIVE/4_relays-17.png"

python3 ../plot.py "$OUTPUT_PLOT_NAIVE"

###############################

cd ../..
cd build

./surrogated-assisted-optimizer pso 4_relays/high-mid/6 0 20 0.8 1.7 1.3
cd "$RUN_DIR"

OUTPUT_PLOT="$OUTPUT_DIR/4_relays-18.png"

python3 ../plot.py "$OUTPUT_PLOT"

cd ../..
cd build

./surrogated-assisted-optimizer naive 4_relays/high-mid/6 0 400

cd "$RUN_DIR"

OUTPUT_PLOT_NAIVE="$OUTPUT_DIR_NAIVE/4_relays-18.png"

python3 ../plot.py "$OUTPUT_PLOT_NAIVE"

###############################

cd ../..
cd build

./surrogated-assisted-optimizer pso 4_relays/high-mid/7 0 20 0.8 1.7 1.3
cd "$RUN_DIR"

OUTPUT_PLOT="$OUTPUT_DIR/4_relays-19.png"

python3 ../plot.py "$OUTPUT_PLOT"

cd ../..
cd build

./surrogated-assisted-optimizer naive 4_relays/high-mid/7 0 400

cd "$RUN_DIR"

OUTPUT_PLOT_NAIVE="$OUTPUT_DIR_NAIVE/4_relays-19.png"

python3 ../plot.py "$OUTPUT_PLOT_NAIVE"

###############################

cd ../..
cd build

./surrogated-assisted-optimizer pso 4_relays/high-mid/8 0 20 0.8 1.7 1.3
cd "$RUN_DIR"

OUTPUT_PLOT="$OUTPUT_DIR/4_relays-20.png"

python3 ../plot.py "$OUTPUT_PLOT"

cd ../..
cd build

./surrogated-assisted-optimizer naive 4_relays/high-mid/8 0 400

cd "$RUN_DIR"

OUTPUT_PLOT_NAIVE="$OUTPUT_DIR_NAIVE/4_relays-20.png"

python3 ../plot.py "$OUTPUT_PLOT_NAIVE"

###############################

cd ../..
cd build

./surrogated-assisted-optimizer pso 4_relays/high-mid/9 0 20 0.8 1.7 1.3
cd "$RUN_DIR"

OUTPUT_PLOT="$OUTPUT_DIR/4_relays-21.png"

python3 ../plot.py "$OUTPUT_PLOT"

cd ../..
cd build

./surrogated-assisted-optimizer naive 4_relays/high-mid/9 0 400

cd "$RUN_DIR"

OUTPUT_PLOT_NAIVE="$OUTPUT_DIR_NAIVE/4_relays-21.png"

python3 ../plot.py "$OUTPUT_PLOT_NAIVE"

###############################

cd ../..
cd build

./surrogated-assisted-optimizer pso 4_relays/high-mid/10 0 20 0.8 1.7 1.3
cd "$RUN_DIR"

OUTPUT_PLOT="$OUTPUT_DIR/4_relays-22.png"

python3 ../plot.py "$OUTPUT_PLOT"

cd ../..
cd build

./surrogated-assisted-optimizer naive 4_relays/high-mid/10 0 400

cd "$RUN_DIR"

OUTPUT_PLOT_NAIVE="$OUTPUT_DIR_NAIVE/4_relays-22.png"

python3 ../plot.py "$OUTPUT_PLOT_NAIVE"

###############################

cd ../..
cd build

./surrogated-assisted-optimizer pso 4_relays/high-mid/11 0 20 0.8 1.7 1.3
cd "$RUN_DIR"

OUTPUT_PLOT="$OUTPUT_DIR/4_relays-23.png"

python3 ../plot.py "$OUTPUT_PLOT"

cd ../..
cd build

./surrogated-assisted-optimizer naive 4_relays/high-mid/11 0 400

cd "$RUN_DIR"

OUTPUT_PLOT_NAIVE="$OUTPUT_DIR_NAIVE/4_relays-23.png"

python3 ../plot.py "$OUTPUT_PLOT_NAIVE"

###############################

cd ../..
cd build

./surrogated-assisted-optimizer pso 4_relays/high-mid/12 0 20 0.8 1.7 1.3
cd "$RUN_DIR"

OUTPUT_PLOT="$OUTPUT_DIR/4_relays-24.png"

python3 ../plot.py "$OUTPUT_PLOT"

cd ../..
cd build

./surrogated-assisted-optimizer naive 4_relays/high-mid/12 0 400

cd "$RUN_DIR"

OUTPUT_PLOT_NAIVE="$OUTPUT_DIR_NAIVE/4_relays-24.png"

python3 ../plot.py "$OUTPUT_PLOT_NAIVE"

###############################