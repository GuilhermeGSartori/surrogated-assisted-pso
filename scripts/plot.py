#!/usr/bin/env python3
"""Create a node/relay plot for every .log file in a directory.

Usage:
    python3 plot_all_logs.py ../../build/logs/final
    python3 plot_all_logs.py ../../build/logs/final --output-dir ./plots

By default, figures are saved in a 'plots' subdirectory of the log directory.
"""

import argparse
from pathlib import Path
import re

import matplotlib
matplotlib.use("Agg")  # Save images without opening a display window.
import matplotlib.pyplot as plt


DEFAULT_LOG_DIR = Path("../../build/logs/final")


def parse_log(filename):
    nodes = []
    first_relays = []
    final_relays = []

    area_width = None
    area_height = None

    reading_nodes = False
    reading_first_relays = False
    reading_final_relays = False

    coordinate_pattern = re.compile(
        r"^\s*"
        r"([-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?)"
        r"\s*,\s*"
        r"([-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?)"
        r"\s*$"
    )

    with open(filename, "r", encoding="utf-8", errors="replace") as file:
        for raw_line in file:
            line = raw_line.strip()

            # ====================================================
            # Area
            # ====================================================
            if line.startswith("Area:"):
                match = re.search(
                    r"Area:\s*([\d.]+)\s*x\s*([\d.]+)", line
                )
                if match:
                    area_width = float(match.group(1))
                    area_height = float(match.group(2))
                continue

            # ====================================================
            # Sensor nodes
            # ====================================================
            if line == "Nodes Positions:":
                reading_nodes = True
                reading_first_relays = False
                reading_final_relays = False
                continue

            # ====================================================
            # Initial relay positions
            # ====================================================
            if line == "First Relays:":
                reading_nodes = False
                reading_first_relays = True
                reading_final_relays = False
                continue

            # ====================================================
            # Final global best relay positions
            # ====================================================
            if line == "Final global best relays:":
                reading_nodes = False
                reading_first_relays = False
                reading_final_relays = True
                continue

            # ====================================================
            # Coordinate parsing
            # ====================================================
            match = coordinate_pattern.fullmatch(line)
            if match:
                position = (float(match.group(1)), float(match.group(2)))

                if reading_nodes:
                    nodes.append(position)
                elif reading_first_relays:
                    first_relays.append(position)
                elif reading_final_relays:
                    final_relays.append(position)
            elif line:
                # Stop a coordinate section at the next heading or log entry.
                # This avoids accidentally treating later particle positions
                # as initial or final relay positions.
                reading_nodes = False
                reading_first_relays = False
                reading_final_relays = False

    return area_width, area_height, nodes, first_relays, final_relays


def plot_nodes(
    area_width,
    area_height,
    nodes,
    first_relays,
    final_relays,
    output_file,
):
    node_x = [node[0] for node in nodes]
    node_y = [node[1] for node in nodes]

    final_relay_x = [relay[0] for relay in final_relays]
    final_relay_y = [relay[1] for relay in final_relays]

    plt.figure(figsize=(8, 8))

    # ============================================================
    # Sensor nodes
    # ============================================================
    plt.scatter(
        node_x,
        node_y,
        color="blue",
        marker="o",
        label="Sensor Nodes",
    )

    # ============================================================
    # Initial relay positions
    # ============================================================
    if first_relays:
        first_relay_x = [relay[0] for relay in first_relays]
        first_relay_y = [relay[1] for relay in first_relays]
        plt.scatter(
            first_relay_x,
            first_relay_y,
            color="green",
            marker="x",
            s=100,
            linewidths=2,
            label="Initial Relays",
        )

    # ============================================================
    # Final global best relay positions
    # ============================================================
    plt.scatter(
        final_relay_x,
        final_relay_y,
        color="red",
        marker="x",
        s=100,
        linewidths=2,
        label="Final Global Best Relays",
    )

    # ============================================================
    # Plot configuration
    # ============================================================
    plt.xlim(0, area_width)
    plt.ylim(0, area_height)
    plt.xlabel("X")
    plt.ylabel("Y")
    plt.title("Sensor Nodes, Initial Relays and Final Global Best Relays")
    plt.grid(True)
    plt.legend()
    plt.gca().set_aspect("equal", adjustable="box")

    plt.savefig(output_file, dpi=300, bbox_inches="tight")
    plt.close()


def main():
    parser = argparse.ArgumentParser(
        description="Create one node/relay PNG for every .log file in a directory."
    )
    parser.add_argument(
        "log_dir",
        type=Path,
        nargs="?",
        default=DEFAULT_LOG_DIR,
        help=f"Directory containing log files (default: {DEFAULT_LOG_DIR})",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory for PNG images (default: LOG_DIR/plots)",
    )
    args = parser.parse_args()

    log_dir = args.log_dir
    output_dir = args.output_dir or log_dir / "plots"

    if not log_dir.is_dir():
        parser.error(f"Log directory does not exist: {log_dir}")

    log_files = sorted(log_dir.glob("*.log"))
    if not log_files:
        print(f"No .log files found in {log_dir}")
        return

    output_dir.mkdir(parents=True, exist_ok=True)

    generated = 0
    skipped = 0

    for log_file in log_files:
        print(f"\nProcessing: {log_file.name}")

        try:
            if "COULD NOT GENERATE RANDOM SOLUTION!!" in log_file.read_text(
                encoding="utf-8", errors="replace"
            ):
                print("  Random solution generation failed. Skipping.")
                skipped += 1
                continue

            area_width, area_height, nodes, first_relays, final_relays = (
                parse_log(log_file)
            )

            if area_width is None or area_height is None:
                print("  No area dimensions found. Skipping.")
                skipped += 1
                continue
            if not nodes:
                print("  No sensor nodes found. Skipping.")
                skipped += 1
                continue
            if not final_relays:
                print("  No final global best relays found. Skipping.")
                skipped += 1
                continue

            output_file = output_dir / f"{log_file.stem}.png"
            plot_nodes(
                area_width,
                area_height,
                nodes,
                first_relays,
                final_relays,
                output_file,
            )
            print(
                f"  Saved: {output_file} "
                f"({len(nodes)} nodes, {len(first_relays)} initial relays, "
                f"{len(final_relays)} final relays)"
            )
            generated += 1
        except Exception as exc:
            print(f"  Error: {exc}. Skipping this log.")
            skipped += 1

    print(f"\nFinished: {generated} plots generated, {skipped} logs skipped.")


if __name__ == "__main__":
    main()