#!/usr/bin/env python3
"""PSO vs. Naive best-so-far convergence at equal simulation budgets.

Run: python3 parse_convergence_checkpoints.py /path/to/logs
Optional: --step 20 --max-budget 400

The default step is 20 FITNESS EVALUATIONS, not 20 complete PSO
iterations. With 20 particles, one population requires 20 evaluations.
Outputs are written under <logs>/parsed_results/.

Naive failures retain the original script's carry-forward convention.
The checkpoint tables flag budgets after such a failure; those budgets
are not evidence of additional successful Naive evaluations.
"""

from pathlib import Path

import re

import csv

import argparse
import statistics
from collections import defaultdict

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

    nodes = extract_int(r"(?:^|\n)Nodes:\s*(\d+)", text)

    network_config = extract_int(
        r"Network Configuration(?:\s+id)?:\s*(\d+)", text
    )

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

        "nodes": nodes,

        "network_config": network_config,

        "width": width,

        "height": height,

    }

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

    running_best = None

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

        # Every Resulting Fitness = one expensive fitness evaluation

        fitness_match = re.search(

            r"Resulting Fitness:\s*([-+0-9.eE]+)",

            line,

            re.IGNORECASE

        )

        if fitness_match:

            evaluation_count += 1

            last_fitness = float(fitness_match.group(1))

            # Reconstruct best-so-far from EVERY evaluation, not only
            # from the optional "New global best!" log message.
            if running_best is None or last_fitness > running_best:
                running_best = last_fitness
                events.append({
                    "iteration": current_iteration,
                    "evaluation": evaluation_count,
                    "fitness": running_best,
                })

            continue

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

        "observed_best": running_best,

        "final_fitness": final_fitness,

        "final_time": final_time,

    }

# ------------------------------------------------------------

# Naive parser

# ------------------------------------------------------------

def parse_naive(path):

    text = path.read_text(errors="replace")

    lines = text.splitlines()

    metadata = get_metadata(text)

    current_iteration = None

    last_iteration = None

    events = []

    for line in lines:

        # Example:

        # ITERATION: 107

        iteration_match = re.search(

            r"ITERATION:\s*(\d+)",

            line,

            re.IGNORECASE

        )

        if iteration_match:

            current_iteration = int(iteration_match.group(1))

            last_iteration = current_iteration

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

            # Iteration 0 corresponds to evaluation 1

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

    # --------------------------------------------------------

    # If Naive failed before printing the normal final result,

    # use the last best fitness it found.

    #

    # If it never found a valid solution, use zero.

    # --------------------------------------------------------

    if final_fitness is None:

        if events:

            final_fitness = events[-1]["fitness"]

        else:

            final_fitness = 0.0

    final_time = extract_float(

        r"Final Evaluation Time:\s*([-+0-9.eE]+)",

        text

    )

    failed_random_solution = bool(

        re.search(

            r"COULD NOT GENERATE RANDOM SOLUTION",

            text,

            re.IGNORECASE

        )

    )

    # Treat Naive as having consumed the complete experiment budget.

    #

    # If it failed to generate another feasible candidate,

    # its current best is simply carried forward until evaluation 400.

    total_evaluations = 400

    return {

        "method": "Naive",

        "path": path,

        "metadata": metadata,

        "events": events,

        "total_evaluations": total_evaluations,

        "last_iteration": last_iteration,

        "final_fitness": final_fitness,

        "final_time": final_time,

        "failed_random_solution": failed_random_solution,

    }

# ------------------------------------------------------------

# Analysis helpers

# ------------------------------------------------------------

def best_at_evaluation(events, evaluation):

    best = None

    for event in events:

        if event["evaluation"] <= evaluation:

            best = max(best, event["fitness"]) if best is not None else event["fitness"]

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

def plot_pair(pair_index, pso, naive, output_dir, common_budget):

    output_dir.mkdir(parents=True, exist_ok=True)

    plt.figure(figsize=(9, 5))

    for run in [pso, naive]:

        visible_events = [
            event for event in run["events"]
            if event["evaluation"] <= common_budget
        ]

        xs = [event["evaluation"] for event in visible_events]

        ys = [event["fitness"] for event in visible_events]

        if not xs:

            if run["method"] == "Naive":

                xs = [1, common_budget]

                ys = [0.0, 0.0]

            else:

                continue

        # Extend curve until common budget

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

    plt.xlim(left=0, right=common_budget)

    plt.ylim(0, 1.02)

    plt.grid(alpha=0.3)

    plt.legend()

    plt.tight_layout()

    filename = output_dir / f"pair_{pair_index:03d}.png"

    plt.savefig(filename, dpi=150)

    plt.close()


# ------------------------------------------------------------
# Checkpoint tables and aggregated convergence
# ------------------------------------------------------------

GROUP_FIELDS = ("relays", "width", "height", "nodes", "network_config")


def write_csv(path, rows, columns):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def checkpoint_summary(checkpoint_rows):
    """Aggregate only PAIRED PSO/Naive results within each configuration."""
    groups = defaultdict(list)

    for row in checkpoint_rows:
        key = tuple(row[name] for name in GROUP_FIELDS) + (row["evaluations"],)
        groups[key].append(row)

    result = []
    for key, rows in groups.items():
        deltas = [row["delta_pdr"] for row in rows]
        tol = 1e-9

        result.append({
            **dict(zip(GROUP_FIELDS, key[:-1])),
            "evaluations": key[-1],
            "pairs": len(rows),
            "mean_pso_pdr": statistics.mean(r["pso_best_pdr"] for r in rows),
            "mean_naive_pdr": statistics.mean(r["naive_best_pdr"] for r in rows),
            "mean_delta_pdr": statistics.mean(deltas),
            "median_delta_pdr": statistics.median(deltas),
            "pso_wins": sum(d > tol for d in deltas),
            "ties": sum(abs(d) <= tol for d in deltas),
            "naive_wins": sum(d < -tol for d in deltas),
            "naive_failed_pairs": sum(r["naive_failed_before_checkpoint"] for r in rows),
        })

    return sorted(result, key=lambda r: (
        tuple(str(r[k]) for k in GROUP_FIELDS), r["evaluations"]
    ))


def best_budget_tables(summary_rows):
    """Exploratory maximum mean advantage, using equally populated budgets."""
    groups = defaultdict(list)
    for row in summary_rows:
        key = tuple(row[name] for name in GROUP_FIELDS)
        groups[key].append(row)

    result = []
    for key, rows in groups.items():
        # Avoid declaring a budget 'best' just because later budgets lost pairs.
        max_pairs = max(row["pairs"] for row in rows)
        comparable = [row for row in rows if row["pairs"] == max_pairs]
        selected = max(comparable, key=lambda r: (r["mean_delta_pdr"],
                                                  -r["evaluations"]))
        result.append({
            **dict(zip(GROUP_FIELDS, key)),
            "candidate_budget_evaluations": selected["evaluations"],
            "mean_delta_pdr": selected["mean_delta_pdr"],
            "mean_pso_pdr": selected["mean_pso_pdr"],
            "mean_naive_pdr": selected["mean_naive_pdr"],
            "pso_wins": selected["pso_wins"],
            "ties": selected["ties"],
            "naive_wins": selected["naive_wins"],
            "pairs": max_pairs,
            "exploratory_only": True,
        })

    return sorted(result, key=lambda r: tuple(str(r[k]) for k in GROUP_FIELDS))


def plot_mean_convergence(summary_rows, output_dir):
    output_dir.mkdir(parents=True, exist_ok=True)
    groups = defaultdict(list)
    for row in summary_rows:
        key = tuple(row[name] for name in GROUP_FIELDS)
        groups[key].append(row)

    for index, (key, rows) in enumerate(sorted(groups.items(), key=lambda kv: str(kv[0])), 1):
        rows = sorted(rows, key=lambda row: row["evaluations"])
        xs = [row["evaluations"] for row in rows]
        n_values = {row["pairs"] for row in rows}
        subtitle = "paired n=" + (str(next(iter(n_values))) if len(n_values) == 1
                                  else "varies; inspect CSV")
        config = dict(zip(GROUP_FIELDS, key))
        title = (f"{config['relays']} relays | {config['width']}×{config['height']} m "
                 f"| nodes={config['nodes']} | network={config['network_config']}\n{subtitle}")

        plt.figure(figsize=(9, 5))
        plt.plot(xs, [row["mean_pso_pdr"] for row in rows], "o-", label="PSO")
        plt.plot(xs, [row["mean_naive_pdr"] for row in rows], "o-", label="Naive")
        plt.xlabel("Fitness evaluations")
        plt.ylabel("Mean best simulated PDR so far")
        plt.title(title)
        plt.grid(alpha=0.3)
        plt.ylim(0, 1.02)
        plt.legend()
        plt.tight_layout()
        plt.savefig(output_dir / f"group_{index:02d}_mean_pdr.png", dpi=150)
        plt.close()

        plt.figure(figsize=(9, 4))
        plt.plot(xs, [row["mean_delta_pdr"] for row in rows], "o-")
        plt.axhline(0, linewidth=1)
        plt.xlabel("Fitness evaluations")
        plt.ylabel("Mean paired advantage (PSO − Naive PDR)")
        plt.title(title)
        plt.grid(alpha=0.3)
        plt.tight_layout()
        plt.savefig(output_dir / f"group_{index:02d}_mean_advantage.png", dpi=150)
        plt.close()

# ------------------------------------------------------------

# Main

# ------------------------------------------------------------

def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(

        "folder",

        help="Folder containing alternating PSO / Naive log files"

    )

    parser.add_argument(

        "--pattern",

        default="*.log",

        help="File pattern, default: *.log"

    )

    parser.add_argument(
        "--step", type=int, default=20,
        help="Checkpoint interval in FITNESS EVALUATIONS (default: 20). "
             "With 20 PSO particles, 20 evaluations is one population."
    )

    parser.add_argument(
        "--max-budget", type=int, default=400,
        help="Maximum common number of fitness evaluations (default: 400)."
    )

    args = parser.parse_args()

    if args.step <= 0 or args.max_budget <= 0:
        parser.error("--step and --max-budget must be positive")

    folder = Path(args.folder)

    files = sorted(

        folder.glob(args.pattern),

        key=natural_key

    )

    if len(files) == 0:

        raise RuntimeError("No files found.")

    output_dir = folder / "parsed_results"

    plot_dir = output_dir / "plots"

    output_dir.mkdir(exist_ok=True)

    event_rows = []

    summary_rows = []

    checkpoint_rows = []

    warned_missing_network_config = False

    # Files normally alternate PSO, Naive, PSO, Naive...

    # If one file is missing, skip the orphan and continue.

    pair_index = 0

    i = 0

    while i < len(files):

        current_file = files[i]

        current_text = current_file.read_text(errors="replace")

        if "Particles:" in current_text:

            current_method = "PSO"

        elif (

            "new best fitness:" in current_text

            or "COULD NOT GENERATE RANDOM SOLUTION" in current_text

            ):

            current_method = "Naive"

        else:

            print(f"Skipping unknown log: {current_file.name}")

            i += 1

            continue

        # A valid pair must start with PSO.

        if current_method != "PSO":

            print(f"Skipping orphan Naive log: {current_file.name}")

            i += 1

            continue

        # PSO is the last file: its Naive partner is missing.

        if i + 1 >= len(files):

            print(f"Skipping PSO with missing Naive log: {current_file.name}")

            break

        next_file = files[i + 1]

        next_text = next_file.read_text(errors="replace")

        if "Particles:" in next_text:

            next_method = "PSO"

        elif ("new best fitness:" in next_text

              or "COULD NOT GENERATE RANDOM SOLUTION" in next_text):

            next_method = "Naive"

        else:

            next_method = None

        # If another PSO comes next, the current PSO's Naive file is missing.

        if next_method != "Naive":

            print(f"Skipping PSO with missing Naive log: {current_file.name}")

            i += 1

            continue

        pair_index += 1

        pso_file = current_file

        naive_file = next_file

        print()

        print(f"Pair {pair_index}")

        print(f"  PSO:   {pso_file.name}")

        print(f"  Naive: {naive_file.name}")

        pso = parse_pso(pso_file)
        naive = parse_naive(naive_file)

        # Naive's relay count is not reliably parsed.
        # Both logs belong to the same paired scenario.
        naive["metadata"]["relays"] = pso["metadata"]["relays"]

        # Consume both files in this valid pair.

        i += 2

        # ----------------------------------------------------

        # Sanity check

        # ----------------------------------------------------

        pso_meta = pso["metadata"]

        naive_meta = naive["metadata"]

        mismatches = []
        for field in ("seed", "relays", "width", "height", "nodes", "network_config"):
            a, b = pso_meta[field], naive_meta[field]
            if a is not None and b is not None and a != b:
                mismatches.append(f"{field}: {a} / {b}")

        if mismatches:
            print("WARNING: skipping mismatched pair: " + "; ".join(mismatches))
            continue

        if pso_meta["network_config"] is None and not warned_missing_network_config:
            print("WARNING: PSO logs lack 'Network Configuration: <id>'. "
                  "Checkpoint tables cannot separate different power settings unless "
                  "this field is available.")
            warned_missing_network_config = True

        if pso["final_fitness"] is not None and pso["observed_best"] is not None:
            if abs(pso["final_fitness"] - pso["observed_best"]) > 1e-5:
                print("WARNING: PSO final fitness differs from its parsed evaluations; "
                      "check for missing or unrelated 'Resulting Fitness' lines")

        if naive["failed_random_solution"]:
            print("WARNING: Naive stopped trying to generate feasible solutions. "
                  "Existing behavior carries its last best through the nominal budget; "
                  "treat later checkpoints as a plateau, not observed evaluations.")

        # ----------------------------------------------------

        # Save improvement events

        # ----------------------------------------------------

        for run in [pso, naive]:

            for event in run["events"]:

                event_rows.append({

                    "pair": pair_index,

                    "method": run["method"],

                    "file": run["path"].name,

                    "seed": run["metadata"]["seed"],

                    "relays": run["metadata"]["relays"],

                    "width": run["metadata"]["width"],

                    "height": run["metadata"]["height"],

                    "nodes": run["metadata"]["nodes"],

                    "network_config": run["metadata"]["network_config"],

                    "iteration": event["iteration"],

                    "evaluation": event["evaluation"],

                    "best_fitness": event["fitness"],

                })

        # ----------------------------------------------------

        # Fair common evaluation budget

        # ----------------------------------------------------

        common_budget = min(

            pso["total_evaluations"],

            naive["total_evaluations"],

            args.max_budget

        )

        # PSO iteration 0 is its initial population; use evaluations,
        # not iteration labels, so the algorithms have equal budgets.
        for checkpoint in range(args.step, common_budget + 1, args.step):
            pso_at_checkpoint = best_at_evaluation(pso["events"], checkpoint)
            naive_at_checkpoint = best_at_evaluation(naive["events"], checkpoint)

            if pso_at_checkpoint is None:
                print(f"WARNING: no PSO fitness available at checkpoint {checkpoint}")
                continue

            if naive_at_checkpoint is None:
                # Same convention as the original script: no feasible solution
                # found yet means zero PDR.
                naive_at_checkpoint = 0.0

            checkpoint_rows.append({
                "pair": pair_index,
                "seed": pso_meta["seed"],
                "relays": pso_meta["relays"],
                "width": pso_meta["width"],
                "height": pso_meta["height"],
                "nodes": pso_meta["nodes"],
                "network_config": pso_meta["network_config"],
                "evaluations": checkpoint,
                "pso_best_pdr": pso_at_checkpoint,
                "naive_best_pdr": naive_at_checkpoint,
                "delta_pdr": pso_at_checkpoint - naive_at_checkpoint,
                "naive_failed": naive["failed_random_solution"],
                "naive_failed_before_checkpoint": (
                    naive["failed_random_solution"] and
                    (naive["last_iteration"] is None or
                     checkpoint > naive["last_iteration"] + 1)
                ),
                "naive_last_logged_iteration": naive["last_iteration"],
            })

        pso_common = best_at_evaluation(

            pso["events"],

            common_budget

        )

        naive_common = best_at_evaluation(

            naive["events"],

            common_budget

        )

        if naive_common is None:

            naive_common = 0.0

        delta_common = None

        if pso_common is not None and naive_common is not None:

            delta_common = pso_common - naive_common

        pso_final_eval = first_evaluation_of_final_best(pso)

        naive_final_eval = first_evaluation_of_final_best(naive)

        summary_rows.append({

            "pair": pair_index,

            "seed": pso_meta["seed"],

            "relays": pso_meta["relays"],

            "width": pso_meta["width"],

            "height": pso_meta["height"],

            "nodes": pso_meta["nodes"],

            "network_config": pso_meta["network_config"],

            "pso_total_evaluations": pso["total_evaluations"],

            "naive_total_evaluations": naive["total_evaluations"],

            "common_budget": common_budget,

            "pso_final_fitness": pso["final_fitness"],

            "naive_final_fitness": naive["final_fitness"],

            "pso_best_common_budget": pso_common,

            "naive_best_common_budget": naive_common,

            "delta_common_budget": delta_common,

            "pso_final_best_first_eval": pso_final_eval,

            "naive_final_best_first_eval": naive_final_eval,

            "pso_final_time": pso["final_time"],

            "naive_final_time": naive["final_time"],

        })

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

        plot_pair(

            pair_index,

            pso,

            naive,

            plot_dir,

            common_budget

        )

    # --------------------------------------------------------

    # CSV output

    # --------------------------------------------------------

    if not summary_rows:
        raise RuntimeError("No valid PSO / Naive pairs found in the folder")

    events_csv = output_dir / "best_events.csv"

    with events_csv.open("w", newline="") as f:

        writer = csv.DictWriter(

            f,

            fieldnames=(event_rows[0].keys() if event_rows else [
                "pair", "method", "file", "seed", "relays", "width", "height",
                "nodes", "network_config", "iteration", "evaluation", "best_fitness"
            ])

        )

        writer.writeheader()

        writer.writerows(event_rows)

    summary_csv = output_dir / "pair_summary.csv"

    with summary_csv.open("w", newline="") as f:

        writer = csv.DictWriter(

            f,

            fieldnames=summary_rows[0].keys()

        )

        writer.writeheader()

        writer.writerows(summary_rows)

    # One row per matched PSO/Naive scenario at each evaluation budget.
    checkpoint_csv = output_dir / "checkpoint_pairs.csv"
    checkpoint_pair_columns = [
        "pair", "seed", *GROUP_FIELDS, "evaluations", "pso_best_pdr",
        "naive_best_pdr", "delta_pdr", "naive_failed",
        "naive_failed_before_checkpoint", "naive_last_logged_iteration"
    ]
    write_csv(checkpoint_csv, checkpoint_rows, checkpoint_pair_columns)

    # Configuration-specific aggregated table across all budgets.
    checkpoint_summary_rows = checkpoint_summary(checkpoint_rows)
    checkpoint_summary_columns = [
        *GROUP_FIELDS, "evaluations", "pairs", "mean_pso_pdr",
        "mean_naive_pdr", "mean_delta_pdr", "median_delta_pdr",
        "pso_wins", "ties", "naive_wins", "naive_failed_pairs"
    ]
    checkpoint_summary_csv = output_dir / "checkpoint_summary.csv"
    write_csv(checkpoint_summary_csv, checkpoint_summary_rows, checkpoint_summary_columns)

    # Separate tables for each checkpoint, e.g. checkpoint_020.csv.
    tables_dir = output_dir / "checkpoint_tables"
    for checkpoint in sorted({row["evaluations"] for row in checkpoint_summary_rows}):
        filename = tables_dir / f"checkpoint_{checkpoint:03d}.csv"
        write_csv(filename,
                  [row for row in checkpoint_summary_rows
                   if row["evaluations"] == checkpoint],
                  checkpoint_summary_columns)

    candidate_csv = output_dir / "exploratory_best_budget.csv"
    candidate_rows = best_budget_tables(checkpoint_summary_rows)
    candidate_columns = [
        *GROUP_FIELDS, "candidate_budget_evaluations", "mean_delta_pdr",
        "mean_pso_pdr", "mean_naive_pdr", "pso_wins", "ties",
        "naive_wins", "pairs", "exploratory_only"
    ]
    write_csv(candidate_csv, candidate_rows, candidate_columns)

    plot_mean_convergence(checkpoint_summary_rows, output_dir / "mean_plots")

    print()

    print("Done.")

    print(f"Summary: {summary_csv}")

    print(f"Events:  {events_csv}")

    print(f"Plots:   {plot_dir}")

    print(f"Pair checkpoints: {checkpoint_csv}")
    print(f"Checkpoint summary: {checkpoint_summary_csv}")
    print(f"Tables per checkpoint: {tables_dir}")
    print(f"Exploratory candidate budgets: {candidate_csv}")
    print(f"Mean convergence plots: {output_dir / 'mean_plots'}")

if __name__ == "__main__":

    main()