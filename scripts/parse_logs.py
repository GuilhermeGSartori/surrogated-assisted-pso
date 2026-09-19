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

        # Every Resulting Fitness = one expensive fitness evaluation
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

def parse_naive(path):
    text = path.read_text(errors="replace")
    lines = text.splitlines()

    metadata = get_metadata(text)

    current_iteration = None
    max_iteration = -1

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
            max_iteration = max(max_iteration, current_iteration)
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

    final_time = extract_float(
        r"Final Evaluation Time:\s*([-+0-9.eE]+)",
        text
    )

    # If every random candidate corresponds to one iteration:
    total_evaluations = max_iteration + 1 if max_iteration >= 0 else 0

    return {
        "method": "Naive",
        "path": path,
        "metadata": metadata,
        "events": events,
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


def plot_pair(pair_index, pso, naive, output_dir):
    output_dir.mkdir(parents=True, exist_ok=True)

    common_budget = min(
        pso["total_evaluations"],
        naive["total_evaluations"]
    )

    plt.figure(figsize=(9, 5))

    for run in [pso, naive]:

        xs = [event["evaluation"] for event in run["events"]]
        ys = [event["fitness"] for event in run["events"]]

        if not xs:
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

    args = parser.parse_args()

    folder = Path(args.folder)

    files = sorted(
        folder.glob(args.pattern),
        key=natural_key
    )

    if len(files) == 0:
        raise RuntimeError("No files found.")

    if len(files) % 2 != 0:
        raise RuntimeError(
            f"Found {len(files)} files. Expected an even number "
            "(PSO/Naive pairs)."
        )

    output_dir = folder / "parsed_results"
    plot_dir = output_dir / "plots"

    output_dir.mkdir(exist_ok=True)

    event_rows = []
    summary_rows = []

    for i in range(0, len(files), 2):

        pair_index = i // 2 + 1

        pso_file = files[i]
        naive_file = files[i + 1]

        print()
        print(f"Pair {pair_index}")
        print(f"  PSO:   {pso_file.name}")
        print(f"  Naive: {naive_file.name}")

        pso = parse_pso(pso_file)
        naive = parse_naive(naive_file)

        # ----------------------------------------------------
        # Sanity check
        # ----------------------------------------------------

        pso_meta = pso["metadata"]
        naive_meta = naive["metadata"]

        if (
            pso_meta["seed"] is not None
            and naive_meta["seed"] is not None
            and pso_meta["seed"] != naive_meta["seed"]
        ):
            print("WARNING: seeds do not match!")

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
                    "iteration": event["iteration"],
                    "evaluation": event["evaluation"],
                    "best_fitness": event["fitness"],
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
            plot_dir
        )

    # --------------------------------------------------------
    # CSV output
    # --------------------------------------------------------

    events_csv = output_dir / "best_events.csv"

    with events_csv.open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=event_rows[0].keys()
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

    print()
    print("Done.")
    print(f"Summary: {summary_csv}")
    print(f"Events:  {events_csv}")
    print(f"Plots:   {plot_dir}")


if __name__ == "__main__":
    main()