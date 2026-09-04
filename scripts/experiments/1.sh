#!/bin/bash

set -e

RUN_DIR="$(pwd)"

SCRIPT_NAME="$(basename "$0")"
SCRIPT_BASE="${SCRIPT_NAME%.*}"

OUTPUT_DIR="$RUN_DIR/$SCRIPT_BASE"
OUTPUT_PLOT="$OUTPUT_DIR/$SCRIPT_BASE.png"

mkdir -p "$OUTPUT_DIR"

echo "=== Building project ==="

cmake -S . -B build
cmake --build build

echo
echo "=== Running optimizer ==="

../../build/surrogated-assisted-optimizer pso 1 0 5 1 1 1

echo
echo "=== Optimizer finished ==="
echo "=== Plotting nodes ==="

python3 ../plot_nodes.py "$OUTPUT_PLOT"

echo "Plot saved to: $OUTPUT_PLOT"