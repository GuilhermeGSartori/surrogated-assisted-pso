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

./surrogated-assisted-optimizer pso 6_relays/1 0 20 0.8 1.7 1.3

cd "$RUN_DIR"

source ../../.venv/bin/activate

OUTPUT_PLOT="$OUTPUT_DIR/6_relays-1.png"

python3 ../plot.py "$OUTPUT_PLOT"

cd ../..
cd build

./surrogated-assisted-optimizer naive 6_relays/1 0 400

cd "$RUN_DIR"

OUTPUT_PLOT_NAIVE="$OUTPUT_DIR_NAIVE/6_relays-1.png"

python3 ../plot.py "$OUTPUT_PLOT_NAIVE"

#######################

cd ../..
cd build

./surrogated-assisted-optimizer pso 6_relays/2 0 20 0.8 1.7 1.3
cd "$RUN_DIR"

OUTPUT_PLOT="$OUTPUT_DIR/6_relays-2.png"

python3 ../plot.py "$OUTPUT_PLOT"

cd ../..
cd build

./surrogated-assisted-optimizer naive 6_relays/2 0 400

cd "$RUN_DIR"

OUTPUT_PLOT_NAIVE="$OUTPUT_DIR_NAIVE/6_relays-2.png"

python3 ../plot.py "$OUTPUT_PLOT_NAIVE"

##################

cd ../..
cd build

./surrogated-assisted-optimizer pso 6_relays/3 0 20 0.8 1.7 1.3
cd "$RUN_DIR"

OUTPUT_PLOT="$OUTPUT_DIR/6_relays-3.png"

python3 ../plot.py "$OUTPUT_PLOT"

cd ../..
cd build

./surrogated-assisted-optimizer naive 6_relays/3 0 400

cd "$RUN_DIR"

OUTPUT_PLOT_NAIVE="$OUTPUT_DIR_NAIVE/6_relays-3.png"

python3 ../plot.py "$OUTPUT_PLOT_NAIVE"

######################

cd ../..
cd build

./surrogated-assisted-optimizer pso 6_relays/4 0 20 0.8 1.7 1.3
cd "$RUN_DIR"

OUTPUT_PLOT="$OUTPUT_DIR/6_relays-4.png"

python3 ../plot.py "$OUTPUT_PLOT"

cd ../..
cd build

./surrogated-assisted-optimizer naive 6_relays/4 0 400

cd "$RUN_DIR"

OUTPUT_PLOT_NAIVE="$OUTPUT_DIR_NAIVE/6_relays-4.png"

python3 ../plot.py "$OUTPUT_PLOT_NAIVE"


######################

cd ../..
cd build

./surrogated-assisted-optimizer pso 6_relays/5 0 20 0.8 1.7 1.3
cd "$RUN_DIR"

OUTPUT_PLOT="$OUTPUT_DIR/6_relays-5.png"

python3 ../plot.py "$OUTPUT_PLOT"

cd ../..
cd build

./surrogated-assisted-optimizer naive 6_relays/5 0 400

cd "$RUN_DIR"

OUTPUT_PLOT_NAIVE="$OUTPUT_DIR_NAIVE/6_relays-5.png"

python3 ../plot.py "$OUTPUT_PLOT_NAIVE"

#############################

cd ../..
cd build

./surrogated-assisted-optimizer pso 6_relays/6 0 20 0.8 1.7 1.3
cd "$RUN_DIR"

OUTPUT_PLOT="$OUTPUT_DIR/6_relays-6.png"

python3 ../plot.py "$OUTPUT_PLOT"

cd ../..
cd build

./surrogated-assisted-optimizer naive 6_relays/6 0 400

cd "$RUN_DIR"

OUTPUT_PLOT_NAIVE="$OUTPUT_DIR_NAIVE/6_relays-6.png"

python3 ../plot.py "$OUTPUT_PLOT_NAIVE"

##############################

cd ../..
cd build

./surrogated-assisted-optimizer pso 6_relays/7 0 20 0.8 1.7 1.3
cd "$RUN_DIR"

OUTPUT_PLOT="$OUTPUT_DIR/6_relays-7.png"

python3 ../plot.py "$OUTPUT_PLOT"

cd ../..
cd build

./surrogated-assisted-optimizer naive 6_relays/7 0 400

cd "$RUN_DIR"

OUTPUT_PLOT_NAIVE="$OUTPUT_DIR_NAIVE/6_relays-7.png"

python3 ../plot.py "$OUTPUT_PLOT_NAIVE"

#############################

cd ../..
cd build

./surrogated-assisted-optimizer pso 6_relays/8 0 20 0.8 1.7 1.3
cd "$RUN_DIR"

OUTPUT_PLOT="$OUTPUT_DIR/6_relays-8.png"

python3 ../plot.py "$OUTPUT_PLOT"

cd ../..
cd build

./surrogated-assisted-optimizer naive 6_relays/8 0 400

cd "$RUN_DIR"

OUTPUT_PLOT_NAIVE="$OUTPUT_DIR_NAIVE/6_relays-8.png"

python3 ../plot.py "$OUTPUT_PLOT_NAIVE"

#############################

cd ../..
cd build

./surrogated-assisted-optimizer pso 6_relays/9 0 20 0.8 1.7 1.3
cd "$RUN_DIR"

OUTPUT_PLOT="$OUTPUT_DIR/6_relays-9.png"

python3 ../plot.py "$OUTPUT_PLOT"

cd ../..
cd build

./surrogated-assisted-optimizer naive 6_relays/9 0 400

cd "$RUN_DIR"

OUTPUT_PLOT_NAIVE="$OUTPUT_DIR_NAIVE/6_relays-9.png"

python3 ../plot.py "$OUTPUT_PLOT_NAIVE"

###############################

cd ../..
cd build

./surrogated-assisted-optimizer pso 6_relays/10 0 20 0.8 1.7 1.3
cd "$RUN_DIR"

OUTPUT_PLOT="$OUTPUT_DIR/6_relays-10.png"

python3 ../plot.py "$OUTPUT_PLOT"

cd ../..
cd build

./surrogated-assisted-optimizer naive 6_relays/10 0 400

cd "$RUN_DIR"

OUTPUT_PLOT_NAIVE="$OUTPUT_DIR_NAIVE/6_relays-10.png"

python3 ../plot.py "$OUTPUT_PLOT_NAIVE"


###############################

cd ../..
cd build

./surrogated-assisted-optimizer pso 6_relays/11 0 20 0.8 1.7 1.3
cd "$RUN_DIR"

OUTPUT_PLOT="$OUTPUT_DIR/6_relays-11.png"

python3 ../plot.py "$OUTPUT_PLOT"

cd ../..
cd build

./surrogated-assisted-optimizer naive 6_relays/11 0 400

cd "$RUN_DIR"

OUTPUT_PLOT_NAIVE="$OUTPUT_DIR_NAIVE/6_relays-11.png"

python3 ../plot.py "$OUTPUT_PLOT_NAIVE"

###########################

cd ../..
cd build

./surrogated-assisted-optimizer pso 6_relays/12 0 20 0.8 1.7 1.3
cd "$RUN_DIR"

OUTPUT_PLOT="$OUTPUT_DIR/6_relays-12.png"

python3 ../plot.py "$OUTPUT_PLOT"

cd ../..
cd build

./surrogated-assisted-optimizer naive 6_relays/12 0 400

cd "$RUN_DIR"

OUTPUT_PLOT_NAIVE="$OUTPUT_DIR_NAIVE/6_relays-12.png"

python3 ../plot.py "$OUTPUT_PLOT_NAIVE"

#####################

cd ../..
cd build

./surrogated-assisted-optimizer pso 6_relays/13 0 20 0.8 1.7 1.3
cd "$RUN_DIR"

OUTPUT_PLOT="$OUTPUT_DIR/6_relays-13.png"

python3 ../plot.py "$OUTPUT_PLOT"

cd ../..
cd build

./surrogated-assisted-optimizer naive 6_relays/13 0 400

cd "$RUN_DIR"

OUTPUT_PLOT_NAIVE="$OUTPUT_DIR_NAIVE/6_relays-13.png"

python3 ../plot.py "$OUTPUT_PLOT_NAIVE"

###########################

cd ../..
cd build

./surrogated-assisted-optimizer pso 6_relays/14 0 20 0.8 1.7 1.3
cd "$RUN_DIR"

OUTPUT_PLOT="$OUTPUT_DIR/6_relays-14.png"

python3 ../plot.py "$OUTPUT_PLOT"

cd ../..
cd build

./surrogated-assisted-optimizer naive 6_relays/14 0 400

cd "$RUN_DIR"

OUTPUT_PLOT_NAIVE="$OUTPUT_DIR_NAIVE/6_relays-14.png"

python3 ../plot.py "$OUTPUT_PLOT_NAIVE"


############################

cd ../..
cd build

./surrogated-assisted-optimizer pso 6_relays/15 0 20 0.8 1.7 1.3
cd "$RUN_DIR"

OUTPUT_PLOT="$OUTPUT_DIR/6_relays-15.png"

python3 ../plot.py "$OUTPUT_PLOT"

cd ../..
cd build

./surrogated-assisted-optimizer naive 6_relays/15 0 400

cd "$RUN_DIR"

OUTPUT_PLOT_NAIVE="$OUTPUT_DIR_NAIVE/6_relays-15.png"

python3 ../plot.py "$OUTPUT_PLOT_NAIVE"
