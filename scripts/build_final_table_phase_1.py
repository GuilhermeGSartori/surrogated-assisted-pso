#!/usr/bin/env python3

import re
import argparse
from pathlib import Path

import pandas as pd


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "input",
        help="TXT file containing the complete experiment output"
    )

    args = parser.parse_args()

    path = Path(args.input)
    text = path.read_text(errors="replace")


    # --------------------------------------------------------
    # Parse every PSO / Naive result
    #
    # Each block begins at "Scenario seed:" and ends before
    # the next scenario.
    # --------------------------------------------------------

    pattern = re.compile(
        r"Scenario seed:\s*(\d+).*?"
        r"Scenario area:\s*(\d+).*?"
        r"Num relays:\s*(\d+).*?"
        r"(PSO|Naive)!"
        r"(.*?)"
        r"(?=\nScenario seed:|\Z)",
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

        else:

            # ------------------------------------------------
            # Failed / incomplete Naive run:
            #
            # use the LAST "new best fitness" found.
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


        rows.append({
            "seed": seed,
            "area": area,
            "relays": relays,
            "method": method,
            "fitness": fitness,
        })


    if not rows:
        raise RuntimeError("No experiment results found.")


    df = pd.DataFrame(rows)

    print(f"Parsed runs: {len(df)}")


    # --------------------------------------------------------
    # Pair PSO and Naive using:
    #
    # seed + area + number of relays
    # --------------------------------------------------------

    paired = df.pivot_table(
        index=["seed", "relays", "area"],
        columns="method",
        values="fitness",
        aggfunc="first"
    ).reset_index()


    # Ignore incomplete pairs
    paired = paired.dropna(
        subset=["PSO", "Naive"]
    )


    # PSO advantage
    paired["delta"] = (
        paired["PSO"]
        - paired["Naive"]
    )


    # --------------------------------------------------------
    # Average delta across seeds
    # --------------------------------------------------------

    summary = (
        paired
        .groupby(["relays", "area"])["delta"]
        .mean()
        .reset_index()
    )


    # --------------------------------------------------------
    # Create table:
    #
    #             Area
    # Relays   350   400   500 ...
    # --------------------------------------------------------

    table = summary.pivot(
        index="relays",
        columns="area",
        values="delta"
    )

    table = table.sort_index()
    table = table.sort_index(axis=1)


    # --------------------------------------------------------
    # Print
    # --------------------------------------------------------

    print()
    print("Mean PSO advantage (PSO - Naive)")
    print()

    print(
        table.to_string(
            float_format=lambda x: f"{x:+.4f}"
        )
    )


    # --------------------------------------------------------
    # Also show number of paired seeds per cell
    # --------------------------------------------------------

    counts = (
        paired
        .groupby(["relays", "area"])
        .size()
        .unstack()
    )

    print()
    print("Number of paired seeds")
    print()

    print(counts.to_string())


    # --------------------------------------------------------
    # Save results
    # --------------------------------------------------------

    output_dir = path.parent / "parsed_table"
    output_dir.mkdir(exist_ok=True)

    paired.to_csv(
        output_dir / "paired_results.csv",
        index=False
    )

    table.to_csv(
        output_dir / "mean_delta_table.csv"
    )

    counts.to_csv(
        output_dir / "seed_count_table.csv"
    )


    print()
    print(f"Saved to: {output_dir}")
    print("  paired_results.csv")
    print("  mean_delta_table.csv")
    print("  seed_count_table.csv")


if __name__ == "__main__":
    main()