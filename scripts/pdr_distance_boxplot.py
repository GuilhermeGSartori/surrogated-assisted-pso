#!/usr/bin/env python3

"""
Create a boxplot of each method's PDR distance from PSO-Sim.

The script pairs runs by sorted filename/timestamp order, matching the
workflow used by the previous comparison scripts.

PDR semantics:
- PSO-Sim:    Final global best fitness = actual OMNeT++ PDR
- Naive-Sim:  Final global best fitness = actual OMNeT++ PDR
- Naive-RF:   Final global best fitness = final OMNeT++ verification PDR
              ("new best fitness" entries are RF predictions)
- PSO-RF:     uses the explicit final OMNeT++ verification line
- Hybrid:     uses the explicit final OMNeT++ verification line

By default the boxplot shows ABSOLUTE PDR distance from PSO-Sim in
percentage points:

    |PDR_method - PDR_PSO-Sim| * 100

Use --signed to instead plot:

    (PDR_method - PDR_PSO-Sim) * 100

Example:

python3 pdr_distance_boxplot.py \
    --pso-sim ../logs/pso_sim \
    --pso-rf ../logs/pso_rf \
    --hybrid ../logs/hybrid \
    --naive-sim ../logs/naive_sim \
    --naive-rf ../logs/naive_rf \
    --expected 12 \
    --out ../logs/pdr_distance_analysis
"""

from pathlib import Path
import argparse
import csv
import re
import statistics

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


NUM = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"

FINAL_FITNESS_RE = re.compile(
    rf"^\s*Final\s+global\s+best\s+fitness:\s*({NUM})",
    re.IGNORECASE | re.MULTILINE,
)

IMPROVEMENT_RE = re.compile(
    rf"^\s*new\s+best\s+fitness:\s*({NUM})",
    re.IGNORECASE | re.MULTILINE,
)

VALIDATED_PDR_PATTERNS = [
    re.compile(
        rf"^\s*Simulation of the best (?:surrogate )?"
        rf"solution results:\s*({NUM})",
        re.IGNORECASE | re.MULTILINE,
    ),
    re.compile(
        rf"^\s*(?:Final|Best)\s+"
        rf"(?:(?:global|selected)\s+best\s+)?"
        rf"(?:actual|simulated|simulation)\s+"
        rf"(?:fitness|PDR):\s*({NUM})",
        re.IGNORECASE | re.MULTILINE,
    ),
    re.compile(
        rf"^\s*(?:Actual|Verified|Validation)\s+"
        rf"(?:simulation\s+)?(?:fitness|PDR):\s*({NUM})",
        re.IGNORECASE | re.MULTILINE,
    ),
    re.compile(
        rf"^\s*Simulation of (?:the )?final "
        rf"(?:best )?(?:solution|layout) "
        rf"(?:results|fitness|PDR):\s*({NUM})",
        re.IGNORECASE | re.MULTILINE,
    ),
]


METHOD_ARGS = [
    ("PSO-RF", "pso_rf"),
    ("Hybrid", "hybrid"),
    ("Naive-Sim", "naive_sim"),
    ("Naive-RF", "naive_rf"),
]


def validate_pdr(value, source):
    if not 0.0 <= value <= 1.0:
        raise ValueError(
            f"PDR outside [0, 1] in {source}: {value}"
        )
    return value


def read_text(path):
    return path.read_text(
        encoding="utf-8",
        errors="replace",
    )


def final_logged_fitness(text):
    matches = list(
        FINAL_FITNESS_RE.finditer(text)
    )

    if not matches:
        return None

    return float(matches[-1].group(1))


def explicit_simulated_pdr(
    text,
    extra_pattern=None,
):
    patterns = list(
        VALIDATED_PDR_PATTERNS
    )

    if extra_pattern is not None:
        patterns.insert(
            0,
            extra_pattern,
        )

    matches = []

    for pattern in patterns:
        for match in pattern.finditer(text):
            matches.append(
                (
                    match.start(),
                    float(match.group(1)),
                    match.group(0).strip(),
                )
            )

    if not matches:
        return None, ""

    _, value, label = max(
        matches,
        key=lambda item: item[0],
    )

    return (
        validate_pdr(
            value,
            label,
        ),
        label,
    )


def actual_pdr(
    path,
    method,
    extra_pattern=None,
):
    text = read_text(path)

    # Direct simulation methods:
    # their final global best fitness is already OMNeT++ PDR.
    if method in (
        "PSO-Sim",
        "Naive-Sim",
    ):
        value = final_logged_fitness(text)

        if value is None:
            raise ValueError(
                "missing 'Final global best fitness'"
            )

        return (
            validate_pdr(
                value,
                path.name,
            ),
            "Final global best fitness",
        )

    # Naive-RF has the special logger behavior discussed previously:
    # "new best fitness" entries are RF predictions, while the FINAL
    # global best fitness is the OMNeT++ verification of the selected layout.
    if method == "Naive-RF":
        value = final_logged_fitness(text)

        if value is None:
            raise ValueError(
                "missing Naive-RF final OMNeT++ fitness"
            )

        return (
            validate_pdr(
                value,
                path.name,
            ),
            "Final global best fitness (Naive-RF final simulation)",
        )

    # PSO-RF and Hybrid:
    # do NOT use Final global best fitness because that may be predicted.
    # Require an explicit final simulation result.
    value, label = explicit_simulated_pdr(
        text,
        extra_pattern,
    )

    if value is None:
        raise ValueError(
            "missing explicit final OMNeT++ verification PDR"
        )

    return value, label


def ordered_logs(folder):
    if not folder.is_dir():
        raise ValueError(
            f"not a directory: {folder}"
        )

    paths = sorted(
        folder.rglob("*.log"),
        key=lambda p: (
            p.name,
            str(p),
        ),
    )

    if not paths:
        raise ValueError(
            f"no .log files found under {folder}"
        )

    return paths


def write_csv(path, rows):
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fieldnames = [
        "scenario_number",
        "method",
        "pso_sim_log",
        "method_log",
        "pso_sim_pdr",
        "method_pdr",
        "signed_difference_pdr",
        "absolute_difference_pdr",
        "signed_difference_pp",
        "absolute_difference_pp",
        "pdr_source",
    ]

    with path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--pso-sim",
        type=Path,
        required=True,
        help="Folder containing PSO-Sim logs.",
    )

    parser.add_argument(
        "--pso-rf",
        type=Path,
        help="Folder containing PSO-RF logs.",
    )

    parser.add_argument(
        "--hybrid",
        type=Path,
        help="Folder containing Hybrid logs.",
    )

    parser.add_argument(
        "--naive-sim",
        type=Path,
        help="Folder containing Naive-Sim logs.",
    )

    parser.add_argument(
        "--naive-rf",
        type=Path,
        help="Folder containing Naive-RF logs.",
    )

    parser.add_argument(
        "--out",
        type=Path,
        default=Path("pdr_distance_analysis"),
        help="Output directory.",
    )

    parser.add_argument(
        "--expected",
        type=int,
        default=None,
        help=(
            "Require exactly N logs per method "
            "(for example: --expected 12)."
        ),
    )

    parser.add_argument(
        "--signed",
        action="store_true",
        help=(
            "Plot signed difference instead of absolute distance. "
            "Signed = method PDR - PSO-Sim PDR."
        ),
    )

    parser.add_argument(
        "--actual-pdr-regex",
        type=str,
        default=None,
        help=(
            "Optional custom regex for the explicit final OMNeT++ PDR "
            "used by PSO-RF/Hybrid. Must contain exactly one capturing group."
        ),
    )

    args = parser.parse_args()

    provided_methods = [
        (
            label,
            getattr(
                args,
                attr,
            ),
        )
        for label, attr in METHOD_ARGS
        if getattr(
            args,
            attr,
        ) is not None
    ]

    if not provided_methods:
        parser.error(
            "provide at least one comparison folder"
        )

    extra_pattern = None

    if args.actual_pdr_regex:
        try:
            extra_pattern = re.compile(
                args.actual_pdr_regex,
                re.IGNORECASE | re.MULTILINE,
            )
        except re.error as exc:
            parser.error(
                f"invalid --actual-pdr-regex: {exc}"
            )

        if extra_pattern.groups != 1:
            parser.error(
                "--actual-pdr-regex must contain exactly "
                "one capturing group"
            )

    try:
        reference_logs = ordered_logs(
            args.pso_sim,
        )
    except ValueError as exc:
        raise SystemExit(
            f"PSO-Sim: {exc}"
        )

    if (
        args.expected is not None
        and len(reference_logs) != args.expected
    ):
        raise SystemExit(
            f"Expected {args.expected} PSO-Sim logs, "
            f"found {len(reference_logs)}."
        )

    method_logs = {}

    for method, folder in provided_methods:
        try:
            logs = ordered_logs(folder)
        except ValueError as exc:
            raise SystemExit(
                f"{method}: {exc}"
            )

        if len(logs) != len(reference_logs):
            raise SystemExit(
                f"Cannot safely pair by order: PSO-Sim has "
                f"{len(reference_logs)} logs but {method} "
                f"has {len(logs)}."
            )

        if (
            args.expected is not None
            and len(logs) != args.expected
        ):
            raise SystemExit(
                f"Expected {args.expected} {method} logs, "
                f"found {len(logs)}."
            )

        method_logs[method] = logs

    print(
        "PAIRING BY SORTED FILENAME/TIMESTAMP ORDER."
    )
    print(
        "This assumes each method ran the same scenarios "
        "in the same order."
    )
    print()

    rows = []
    values_by_method = {
        method: []
        for method, _ in provided_methods
    }

    for index, reference_path in enumerate(
        reference_logs,
        start=1,
    ):
        try:
            reference_pdr, _ = actual_pdr(
                reference_path,
                "PSO-Sim",
                extra_pattern,
            )
        except ValueError as exc:
            print(
                f"SKIP scenario {index}: "
                f"PSO-Sim {reference_path.name}: {exc}"
            )
            continue

        for method, _ in provided_methods:
            candidate_path = method_logs[
                method
            ][index - 1]

            try:
                candidate_pdr, pdr_source = actual_pdr(
                    candidate_path,
                    method,
                    extra_pattern,
                )
            except ValueError as exc:
                print(
                    f"SKIP {method}, scenario {index}: "
                    f"{candidate_path.name}: {exc}"
                )
                continue

            signed = (
                candidate_pdr
                - reference_pdr
            )

            absolute = abs(
                signed
            )

            signed_pp = (
                signed
                * 100.0
            )

            absolute_pp = (
                absolute
                * 100.0
            )

            rows.append(
                {
                    "scenario_number": index,
                    "method": method,
                    "pso_sim_log": str(
                        reference_path
                    ),
                    "method_log": str(
                        candidate_path
                    ),
                    "pso_sim_pdr": reference_pdr,
                    "method_pdr": candidate_pdr,
                    "signed_difference_pdr": signed,
                    "absolute_difference_pdr": absolute,
                    "signed_difference_pp": signed_pp,
                    "absolute_difference_pp": absolute_pp,
                    "pdr_source": pdr_source,
                }
            )

            values_by_method[
                method
            ].append(
                signed_pp
                if args.signed
                else absolute_pp
            )

    nonempty_methods = [
        method
        for method, values
        in values_by_method.items()
        if values
    ]

    if not nonempty_methods:
        raise SystemExit(
            "No valid paired PDR values were found."
        )

    args.out.mkdir(
        parents=True,
        exist_ok=True,
    )

    csv_path = (
        args.out
        / "pdr_distance_by_scenario.csv"
    )

    write_csv(
        csv_path,
        rows,
    )

    data = [
        values_by_method[
            method
        ]
        for method in nonempty_methods
    ]

    labels = [
        f"{method}\n"
        f"(n={len(values_by_method[method])})"
        for method in nonempty_methods
    ]

    fig, ax = plt.subplots(
        figsize=(9, 5.5)
    )

    ax.boxplot(
        data,
        labels=labels,
        showmeans=True,
    )

    if args.signed:
        ax.axhline(
            0.0,
            linewidth=1.0,
        )

        ax.set_ylabel(
            "PDR difference from PSO-Sim "
            "(percentage points)"
        )

        ax.set_title(
            "PDR difference relative to PSO-Sim "
            "across paired scenarios"
        )
    else:
        ax.set_ylabel(
            "Absolute PDR distance from PSO-Sim "
            "(percentage points)"
        )

        ax.set_title(
            "Absolute PDR distance from PSO-Sim "
            "across paired scenarios"
        )

    ax.grid(
        axis="y",
        alpha=0.35,
    )

    fig.tight_layout()

    plot_name = (
        "pdr_signed_difference_boxplot.png"
        if args.signed
        else "pdr_distance_boxplot.png"
    )

    plot_path = (
        args.out
        / plot_name
    )

    fig.savefig(
        plot_path,
        dpi=250,
    )

    plt.close(
        fig
    )

    print(
        f"Saved {plot_path}"
    )
    print(
        f"Saved {csv_path}"
    )
    print()
    print(
        "Summary relative to PSO-Sim:"
    )

    for method in nonempty_methods:
        values = values_by_method[
            method
        ]

        mean_value = statistics.mean(
            values
        )

        median_value = statistics.median(
            values
        )

        stdev_value = (
            statistics.stdev(values)
            if len(values) > 1
            else 0.0
        )

        metric_name = (
            "signed gap"
            if args.signed
            else "absolute distance"
        )

        print(
            f"  {method:10s} "
            f"n={len(values):2d}  "
            f"mean {metric_name}="
            f"{mean_value:.3f} pp  "
            f"median={median_value:.3f} pp  "
            f"sd={stdev_value:.3f} pp"
        )


if __name__ == "__main__":
    main()
