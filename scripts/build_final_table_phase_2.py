#!/usr/bin/env python3

import re
import argparse
from pathlib import Path

import pandas as pd


# ------------------------------------------------------------
# Network configurations
#
# config:
#   relay power
#   node power
# ------------------------------------------------------------

NETWORK_CONFIGS = {
    1: (0.00224,  0.00224),
    2: (0.00224,  0.001),
    3: (0.00224,  0.000316),

    4: (0.001,    0.00224),
    5: (0.001,    0.001),
    6: (0.001,    0.000316),

    7: (0.000316, 0.00224),
    8: (0.000316, 0.001),
    9: (0.000316, 0.000316),
}


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "input",
        help="TXT file containing the complete Phase 2 experiment output"
    )

    args = parser.parse_args()

    path = Path(args.input)
    text = path.read_text(errors="replace")


    # --------------------------------------------------------
    # Parse every PSO / Naive block
    #
    # Each block begins with:
    #
    # Scenario seed:
    #
    # and ends immediately before the next scenario.
    # --------------------------------------------------------

    pattern = re.compile(
        r"Scenario seed:\s*(\d+).*?"
        r"Scenario area:\s*(\d+).*?"
        r"Num relays:\s*(\d+).*?"
        r"(PSO|Naive)!"
        r"(.*?)"
        r"(?=\n>>>\s*\nScenario seed:|\nScenario seed:|\Z)",
        re.DOTALL | re.IGNORECASE
    )


    rows = []


    for match in pattern.finditer(text):

        seed = int(match.group(1))
        area = int(match.group(2))
        relays = int(match.group(3))

        method = (
            "PSO"
            if match.group(4).lower() == "pso"
            else "Naive"
        )

        body = match.group(5)


        # ----------------------------------------------------
        # Normal completed run
        # ----------------------------------------------------

        final_match = re.search(
            r"Final global best fitness:\s*([-+0-9.eE]+)",
            body,
            re.IGNORECASE
        )


        if final_match:

            fitness = float(final_match.group(1))
            failed = False


        else:

            # ------------------------------------------------
            # Incomplete/failed Naive run.
            #
            # Use the LAST best value if one exists.
            # Otherwise use zero.
            # ------------------------------------------------

            best_values = re.findall(
                r"new best fitness:\s*([-+0-9.eE]+)",
                body,
                re.IGNORECASE
            )

            if best_values:
                fitness = float(best_values[-1])
            else:
                fitness = 0.0

            failed = True


        rows.append({
            "seed": seed,
            "area": area,
            "relays": relays,
            "method": method,
            "fitness": fitness,
            "failed": failed,
        })


    if not rows:
        raise RuntimeError("No experiment results found.")


    df = pd.DataFrame(rows)

    print(f"Parsed runs: {len(df)}")


    # --------------------------------------------------------
    # Recover network configuration from execution order.
    #
    # For every:
    #
    # seed + relay count + method
    #
    # execution 1 = network config 1
    # execution 2 = network config 2
    # ...
    # execution 9 = network config 9
    #
    # Using the method separately means PSO execution #1 is
    # paired with Naive execution #1, etc.
    # --------------------------------------------------------

    df["network_config"] = (
        df
        .groupby(["seed", "relays", "method"])
        .cumcount()
        + 1
    )


    # --------------------------------------------------------
    # Verify expected number of configurations
    # --------------------------------------------------------

    invalid = df[
        ~df["network_config"].between(1, 9)
    ]

    if not invalid.empty:
        raise RuntimeError(
            "More than 9 executions found for at least one "
            "seed/relay/method combination."
        )


    # --------------------------------------------------------
    # Assign actual powers
    # --------------------------------------------------------

    df["relay_power"] = df["network_config"].map(
        lambda config: NETWORK_CONFIGS[config][0]
    )

    df["node_power"] = df["network_config"].map(
        lambda config: NETWORK_CONFIGS[config][1]
    )


    # --------------------------------------------------------
    # Pair PSO and Naive
    # --------------------------------------------------------

    paired = df.pivot_table(
        index=[
            "seed",
            "relays",
            "area",
            "network_config",
            "relay_power",
            "node_power",
        ],
        columns="method",
        values="fitness",
        aggfunc="first"
    ).reset_index()


    paired = paired.dropna(
        subset=["PSO", "Naive"]
    )


    paired["delta"] = (
        paired["PSO"]
        - paired["Naive"]
    )


    # --------------------------------------------------------
    # Add information about failed runs
    # --------------------------------------------------------

    failed_table = df.pivot_table(
        index=[
            "seed",
            "relays",
            "area",
            "network_config",
            "relay_power",
            "node_power",
        ],
        columns="method",
        values="failed",
        aggfunc="first"
    ).reset_index()


    paired = paired.merge(
        failed_table,
        on=[
            "seed",
            "relays",
            "area",
            "network_config",
            "relay_power",
            "node_power",
        ],
        suffixes=("", "_failed")
    )


    # --------------------------------------------------------
    # Average PSO advantage across seeds
    # --------------------------------------------------------

    summary = (
        paired
        .groupby([
            "relays",
            "relay_power",
            "node_power"
        ])["delta"]
        .mean()
        .reset_index()
    )


    # --------------------------------------------------------
    # Output directory
    # --------------------------------------------------------

    output_dir = path.parent / "parsed_power_tables"
    output_dir.mkdir(exist_ok=True)


    # --------------------------------------------------------
    # Full paired results
    # --------------------------------------------------------

    paired.to_csv(
        output_dir / "paired_power_results.csv",
        index=False
    )

    summary.to_csv(
        output_dir / "mean_power_delta.csv",
        index=False
    )


    # --------------------------------------------------------
    # Print one 3x3 table for every relay count
    #
    # Rows    = Relay power
    # Columns = Node power
    # Values  = mean PSO - Naive
    # --------------------------------------------------------

    for relays in sorted(summary["relays"].unique()):

        relay_data = summary[
            summary["relays"] == relays
        ]


        table = relay_data.pivot(
            index="relay_power",
            columns="node_power",
            values="delta"
        )


        # Higher powers first
        table = table.sort_index(
            ascending=False
        )

        table = table.sort_index(
            axis=1,
            ascending=False
        )


        print()
        print("=" * 70)
        print(f"{relays} RELAYS")
        print("Mean PSO advantage (PSO - Naive)")
        print("Rows = relay power | Columns = node power")
        print("=" * 70)
        print()

        print(
            table.to_string(
                float_format=lambda x: f"{x:+.4f}"
            )
        )


        table.to_csv(
            output_dir /
            f"mean_delta_{relays}_relays.csv"
        )


    # --------------------------------------------------------
    # Combined table
    #
    # Rows:
    #   relay count + relay power
    #
    # Columns:
    #   node power
    # --------------------------------------------------------

    combined = summary.pivot_table(
        index=[
            "relays",
            "relay_power"
        ],
        columns="node_power",
        values="delta"
    )

    combined = combined.sort_index(
        level=[0, 1],
        ascending=[True, False]
    )

    combined = combined.sort_index(
        axis=1,
        ascending=False
    )


    print()
    print("=" * 70)
    print("COMBINED TABLE")
    print("=" * 70)
    print()

    print(
        combined.to_string(
            float_format=lambda x: f"{x:+.4f}"
        )
    )


    combined.to_csv(
        output_dir / "combined_power_table.csv"
    )


    # --------------------------------------------------------
    # Count Naive failures
    #
    # Useful because fitness = 0 when Naive could not generate
    # any feasible solution.
    # --------------------------------------------------------

    naive_runs = df[
        df["method"] == "Naive"
    ]

    failure_counts = (
        naive_runs
        .groupby([
            "relays",
            "relay_power",
            "node_power"
        ])["failed"]
        .sum()
        .reset_index()
    )


    failure_counts.to_csv(
        output_dir / "naive_failure_counts.csv",
        index=False
    )


    print()
    print("Naive failure counts")
    print()

    for relays in sorted(
        failure_counts["relays"].unique()
    ):

        failure_table = (
            failure_counts[
                failure_counts["relays"] == relays
            ]
            .pivot(
                index="relay_power",
                columns="node_power",
                values="failed"
            )
            .sort_index(ascending=False)
            .sort_index(
                axis=1,
                ascending=False
            )
        )

        print()
        print(f"{relays} relays:")
        print(failure_table.to_string())


    print()
    print(f"Saved to: {output_dir}")
    print("  paired_power_results.csv")
    print("  mean_power_delta.csv")
    print("  combined_power_table.csv")
    print("  naive_failure_counts.csv")

    for relays in sorted(
        summary["relays"].unique()
    ):
        print(
            f"  mean_delta_{relays}_relays.csv"
        )


if __name__ == "__main__":
    main()