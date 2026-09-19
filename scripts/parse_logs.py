#!/usr/bin/env python3

from pathlib import Path
import re
import csv
import argparse
import matplotlib.pyplot as plt


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

def natural_key(path):
    """
    Natural sorting:
    log2.txt comes before log10.txt.
    """
    return [
        int(part) if part.isdigit() else part.lower()
        for part in re.split(r"(\d+)", path.name)
    ]


def extract_float(pattern, text, default=None):
    match = re.search(pattern, text, re.IGNORECASE)

    if match:
        return float(match.group(1))

    return default


def extract_int(pattern, text, default=None):
    match = re.search(pattern, text, re.IGNORECASE)

    if match:
        return int(match.group(1))

    return default


def get_metadata(text):
    seed = extract_int(r"Seed:\s*(\d+)", text)
    relays = extract_int(r"Relays:\s*(\d+)", text)

    area_match = re.search(
        r"Area:\s*([0-9.]+)\s*x\s*([0-9.]+)",
        text,
        re.IGNORECASE
    )

    if area_match:
        width = float(area_match.group(1))
        height = float(area_match.group(2))
    else:
        width = None
        height = None

    return {
        "seed": seed,
        "relays": relays,
        "width": width,
        "height": height,
    }


def scenario_key(metadata):
    return (
        metadata["seed"],
        metadata["relays"],
        metadata["width"],
        metadata["height"],
    )


def detect_method(text):
    """
    Detect whether the log belongs to PSO or Naive.
    """

    if (
        re.search(r"PSO EXECUTION", text, re.IGNORECASE)
        or re.search(r"Particles:\s*\d+", text, re.IGNORECASE)
    ):
        return "PSO"

    if re.search(r"new best fitness:", text, re.IGNORECASE):
        return "Naive"

    return None


# ------------------------------------------------------------
# PSO parser
# ------------------------------------------------------------

def parse_pso(path):
    text = path.read_text(errors="replace")
    lines = text.splitlines()

    metadata = get_metadata(text)

    current_iteration = None
    evaluation_count = 0
    last_fitness = None

    events = []

    for line in lines:

        # Example:
        # -- ITERATION 3 --
        iteration_match = re.search(
            r"--\s*ITERATION\s+(\d+)\s*--",
            line,
            re.IGNORECASE
        )

        if iteration_match:
            current_iteration = int(iteration_match.group(1))
            continue

        # Every Resulting Fitness = one actual fitness evaluation
        fitness_match = re.search(
            r"Resulting Fitness:\s*([-+0-9.eE]+)",
            line,
            re.IGNORECASE
        )

        if fitness_match:
            evaluation_count += 1
            last_fitness = float(fitness_match.group(1))
            continue

        # The previous Resulting Fitness became the new global best
        if re.search(r"New global best!", line, re.IGNORECASE):

            if last_fitness is not None:
                events.append({
                    "iteration": current_iteration,
                    "evaluation": evaluation_count,
                    "fitness": last_fitness,
                })

    final_fitness = extract_float(
        r"Final global best fitness:\s*([-+0-9.eE]+)",
        text
    )

    final_time = extract_float(
        r"Final Evaluation Time:\s*([-+0-9.eE]+)",
        text
    )

    return {
        "method": "PSO",
        "path": path,
        "metadata": metadata,
        "events": events,
        "total_evaluations": evaluation_count,
        "final_fitness": final_fitness,
        "final_time": final_time,
    }


# ------------------------------------------------------------
# Naive parser
# ------------------------------------------------------------

def parse_naive(path, total_evaluations=400):
    text = path.read_text(errors="replace")
    lines = text.splitlines()

    metadata = get_metadata(text)

    current_iteration = None
    events = []

    for line in lines:

        # Example:
        # ITERATION: 107
        #
        # Important:
        # Naive only logs the iteration when a new best is found.
        iteration_match = re.search(
            r"ITERATION:\s*(\d+)",
            line,
            re.IGNORECASE
        )

        if iteration_match:
            current_iteration = int(iteration_match.group(1))
            continue

        # Example:
        # new best fitness: 0.966667
        best_match = re.search(
            r"new best fitness:\s*([-+0-9.eE]+)",
            line,
            re.IGNORECASE
        )

        if best_match and current_iteration is not None:

            fitness = float(best_match.group(1))

            # ITERATION 0 = fitness evaluation 1
            evaluation = current_iteration + 1

            events.append({
                "iteration": current_iteration,
                "evaluation": evaluation,
                "fitness": fitness,
            })

    final_fitness = extract_float(
        r"Final global best fitness:\s*([-+0-9.eE]+)",
        text
    )

    final_time = extract_float(
        r"Final Evaluation Time:\s*([-+0-9.eE]+)",
        text
    )

    return {
        "method": "Naive",
        "path": path,
        "metadata": metadata,
        "events": events,

        # Naive actually performs all 400 evaluations.
        # It simply does not log every one of them.
        "total_evaluations": total_evaluations,

        "final_fitness": final_fitness,
        "final_time": final_time,
    }


# ------------------------------------------------------------
# Analysis helpers
# ------------------------------------------------------------

def best_at_evaluation(events, evaluation):
    best = None

    for event in events:

        if event["evaluation"] <= evaluation:
            best = event["fitness"]

        else:
            break

    return best


def first_evaluation_of_final_best(run):
    final = run["final_fitness"]

    if final is None:
        return None

    for event in run["events"]:

        if abs(event["fitness"] - final) < 1e-9:
            return event["evaluation"]

    # Usually the last improvement corresponds to final best
    if run["events"]:
        return run["events"][-1]["evaluation"]

    return None


# ------------------------------------------------------------
# Plot
# ------------------------------------------------------------

def plot_pair(pair_index, pso, naive, output_dir):
    output_dir.mkdir(parents=True, exist_ok=True)

    common_budget = min(
        pso["total_evaluations"],
        naive["total_evaluations"]
    )

    plt.figure(figsize=(9, 5))

    for run in [pso, naive]:

        # Only include events inside the fair evaluation budget
        events = [
            event
            for event in run["events"]
            if event["evaluation"] <= common_budget
        ]

        if not events:
            continue

        xs = [
            event["evaluation"]
            for event in events
        ]

        ys = [
            event["fitness"]
            for event in events
        ]

        # Extend the final known best until the end of the budget
        if xs[-1] < common_budget:
            xs.append(common_budget)
            ys.append(ys[-1])

        plt.step(
            xs,
            ys,
            where="post",
            label=run["method"]
        )

    meta = pso["metadata"]

    title = (
        f"Seed={meta['seed']} | "
        f"Relays={meta['relays']} | "
        f"Area={meta['width']}x{meta['height']}"
    )

    plt.title(title)
    plt.xlabel("Fitness evaluations")
    plt.ylabel("Best PDR found so far")

    plt.xlim(
        left=0,
        right=common_budget
    )

    plt.ylim(
        0,
        1.02
    )

    plt.grid(alpha=0.3)
    plt.legend()
    plt.tight_layout()

    filename = output_dir / f"pair_{pair_index:03d}.png"

    plt.savefig(
        filename,
        dpi=150
    )

    plt.close()


# ------------------------------------------------------------
# Main
# ------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "folder",
        help="Folder containing PSO and Naive log files"
    )

    parser.add_argument(
        "--pattern",
        default="*.log",
        help="File pattern, default: *.log"
    )

    args = parser.parse_args()

    folder = Path(args.folder)

    files = sorted(
        folder.glob(args.pattern),
        key=natural_key
    )

    if len(files) == 0:
        raise RuntimeError("No files found.")

    # --------------------------------------------------------
    # Build scenario groups
    #
    # Instead of:
    #
    # file 1 -> PSO
    # file 2 -> Naive
    #
    # we pair using:
    #
    # (seed, relays, area)
    #
    # This prevents one missing file from shifting every pair.
    # --------------------------------------------------------

    scenarios = {}

    for path in files:

        text = path.read_text(errors="replace")

        method = detect_method(text)
        metadata = get_metadata(text)

        if method is None:
            print(f"Skipping unknown file: {path.name}")
            continue

        if (
            metadata["seed"] is None
            or metadata["relays"] is None
            or metadata["width"] is None
            or metadata["height"] is None
        ):
            print(f"Skipping file with missing metadata: {path.name}")
            continue

        key = scenario_key(metadata)

        if key not in scenarios:
            scenarios[key] = {}

        scenarios[key][method] = path

    # --------------------------------------------------------
    # Output directories
    # --------------------------------------------------------

    output_dir = folder / "parsed_results"
    plot_dir = output_dir / "plots"

    output_dir.mkdir(exist_ok=True)

    event_rows = []
    summary_rows = []

    pair_index = 0

    # Sort:
    #
    # relays -> area -> seed
    scenario_keys = sorted(
        scenarios.keys(),
        key=lambda key: (
            key[1],
            key[2],
            key[0]
        )
    )

    # --------------------------------------------------------
    # Process complete pairs
    # --------------------------------------------------------

    for key in scenario_keys:

        runs = scenarios[key]

        # If PSO or Naive is missing, simply ignore this scenario.
        if "PSO" not in runs or "Naive" not in runs:

            print(
                f"Skipping incomplete scenario: "
                f"seed={key[0]}, "
                f"relays={key[1]}, "
                f"area={key[2]}x{key[3]}"
            )

            continue

        pair_index += 1

        pso_file = runs["PSO"]
        naive_file = runs["Naive"]

        print()
        print(f"Pair {pair_index}")
        print(f"  PSO:   {pso_file.name}")
        print(f"  Naive: {naive_file.name}")

        pso = parse_pso(pso_file)

        # Naive has exactly 400 actual simulation evaluations
        naive = parse_naive(
            naive_file,
            total_evaluations=400
        )

        # ----------------------------------------------------
        # Metadata sanity check
        # ----------------------------------------------------

        pso_meta = pso["metadata"]
        naive_meta = naive["metadata"]

        if pso_meta != naive_meta:
            print("WARNING: scenario metadata do not match!")

        # ----------------------------------------------------
        # Save improvement events
        # ----------------------------------------------------

        for run in [pso, naive]:

            for event in run["events"]:

                event_rows.append({
                    "pair": pair_index,
                    "method": run["method"],
                    "file": run["path"].name,

                    "seed":
                        run["metadata"]["seed"],

                    "relays":
                        run["metadata"]["relays"],

                    "width":
                        run["metadata"]["width"],

                    "height":
                        run["metadata"]["height"],

                    "iteration":
                        event["iteration"],

                    "evaluation":
                        event["evaluation"],

                    "best_fitness":
                        event["fitness"],
                })

        # ----------------------------------------------------
        # Fair common evaluation budget
        # ----------------------------------------------------

        common_budget = min(
            pso["total_evaluations"],
            naive["total_evaluations"]
        )

        pso_common = best_at_evaluation(
            pso["events"],
            common_budget
        )

        naive_common = best_at_evaluation(
            naive["events"],
            common_budget
        )

        delta_common = None

        if (
            pso_common is not None
            and naive_common is not None
        ):
            delta_common = (
                pso_common - naive_common
            )

        # ----------------------------------------------------
        # Evaluation where final best was first found
        # ----------------------------------------------------

        pso_final_eval = (
            first_evaluation_of_final_best(pso)
        )

        naive_final_eval = (
            first_evaluation_of_final_best(naive)
        )

        # ----------------------------------------------------
        # Summary
        # ----------------------------------------------------

        summary_rows.append({
            "pair":
                pair_index,

            "seed":
                pso_meta["seed"],

            "relays":
                pso_meta["relays"],

            "width":
                pso_meta["width"],

            "height":
                pso_meta["height"],

            "pso_total_evaluations":
                pso["total_evaluations"],

            "naive_total_evaluations":
                naive["total_evaluations"],

            "common_budget":
                common_budget,

            "pso_final_fitness":
                pso["final_fitness"],

            "naive_final_fitness":
                naive["final_fitness"],

            "pso_best_common_budget":
                pso_common,

            "naive_best_common_budget":
                naive_common,

            "delta_common_budget":
                delta_common,

            "pso_final_best_first_eval":
                pso_final_eval,

            "naive_final_best_first_eval":
                naive_final_eval,

            "pso_final_time":
                pso["final_time"],

            "naive_final_time":
                naive["final_time"],
        })

        # ----------------------------------------------------
        # Console output
        # ----------------------------------------------------

        print(
            f"  evaluations: "
            f"PSO={pso['total_evaluations']}, "
            f"Naive={naive['total_evaluations']}"
        )

        print(
            f"  final best first found: "
            f"PSO={pso_final_eval}, "
            f"Naive={naive_final_eval}"
        )

        print(
            f"  common budget={common_budget}: "
            f"PSO={pso_common}, "
            f"Naive={naive_common}, "
            f"delta={delta_common}"
        )

        # ----------------------------------------------------
        # Plot
        # ----------------------------------------------------

        plot_pair(
            pair_index,
            pso,
            naive,
            plot_dir
        )

    # --------------------------------------------------------
    # CSV output
    # --------------------------------------------------------

    events_csv = output_dir / "best_events.csv"

    if event_rows:

        with events_csv.open(
            "w",
            newline=""
        ) as f:

            writer = csv.DictWriter(
                f,
                fieldnames=event_rows[0].keys()
            )

            writer.writeheader()
            writer.writerows(event_rows)

    summary_csv = output_dir / "pair_summary.csv"

    if summary_rows:

        with summary_csv.open(
            "w",
            newline=""
        ) as f:

            writer = csv.DictWriter(
                f,
                fieldnames=summary_rows[0].keys()
            )

            writer.writeheader()
            writer.writerows(summary_rows)

    print()
    print("Done.")

    print(
        f"Complete pairs parsed: "
        f"{pair_index}"
    )

    print(
        f"Summary: "
        f"{summary_csv}"
    )

    print(
        f"Events: "
        f"{events_csv}"
    )

    print(
        f"Plots: "
        f"{plot_dir}"
    )


if __name__ == "__main__":
    main()