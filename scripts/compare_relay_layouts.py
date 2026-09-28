#!/usr/bin/env python3
"""Compare final relay layouts from multiple methods against PSO + simulation.

Use --by-order when Naive logs contain only final relay coordinates, without
scenario metadata. The Nth timestamp-sorted log in each method folder is paired
with the Nth PSO-Sim log. This assumes all methods ran the SAME scenario order.

For one mixed folder, use --combined-dir and specify --sequence and whether
the logs are interleaved by scenario or grouped by method.

Without --by-order, match by seed AND logged sensor-node coordinates.
Relay IDs are arbitrary: use minimum-cost one-to-one assignment instead of
comparing relay 0 with relay 0, relay 1 with relay 1, etc.

Example:
  python3 compare_relay_layouts_with_pdr_naive_rf_fixed.py \
      --pso-sim ../build/logs/pso_sim \
      --pso-rf ../build/logs/pso_rf \
      --hybrid ../build/logs/hybrid \
      --naive-sim ../build/logs/naive_sim \
      --naive-rf ../build/logs/naive_rf \
      --by-order --out ../build/logs/layout_comparison

  python3 compare_relay_layouts_with_pdr_naive_rf_fixed.py \
      --combined-dir ../build/logs/final \
      --sequence pso_sim naive_sim pso_rf naive_rf hybrid \
      --combined-order interleaved --out ../build/logs/layout_comparison

The logged final global best may be RF-predicted for surrogate backends.
An explicit final simulation verification is extracted separately, when present.
Missing actual PDR stays missing, rather than silently using a prediction.

Dependencies: numpy, scipy, matplotlib.
"""

import argparse
import csv
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, replace
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # Generate figures without opening plot windows.
import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import linear_sum_assignment

NUM = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
COORD_RE = re.compile(rf"^\s*({NUM})\s*,\s*({NUM})\s*,?\s*$")
AREA_RE = re.compile(rf"^\s*Area:\s*({NUM})\s*[x×]\s*({NUM})", re.I | re.M)
SEED_RE = re.compile(r"^\s*(?:Scenario\s+)?Seed:\s*(\d+)\b", re.I | re.M)
RELAY_COUNT_RE = re.compile(r"^\s*(?:Num(?:ber\s+of)?\s+)?Relays:\s*(\d+)\b", re.I | re.M)
NETWORK_RE = re.compile(r"^\s*Network\s+Configuration(?:\s+(?:ID|id))?:\s*(\d+)\b", re.I | re.M)
SINK_RE = re.compile(rf"^\s*Sink(?:\s+(?:Position|Coordinates))?:\s*\(?\s*({NUM})\s*[,;]\s*({NUM})\s*\)?", re.I | re.M)
FITNESS_RE = re.compile(rf"^\s*Final\s+global\s+best\s+fitness:\s*({NUM})", re.I | re.M)
# PSO-RF/Hybrid usually log their RF prediction as final global best fitness,
# then print an explicit final OMNeT++ verification. Naive-RF uses a DIFFERENT
# format: its "new best fitness" lines are RF predictions, while its final
# "Final global best fitness" is the final OMNeT++ verification.
# Preserve those separate meanings and apply the Naive-RF fallback ONLY there.
IMPROVEMENT_RE = re.compile(rf"^\s*new best fitness:\s*({NUM})", re.I | re.M)
VALIDATED_PDR_PATTERNS = [
    re.compile(rf"^\s*Simulation of the best (?:surrogate )?solution results:\s*({NUM})", re.I | re.M),
    re.compile(rf"^\s*(?:Final|Best)\s+(?:(?:global|selected)\s+best\s+)?(?:actual|simulated|simulation)\s+(?:fitness|PDR):\s*({NUM})", re.I | re.M),
    re.compile(rf"^\s*(?:Actual|Verified|Validation)\s+(?:simulation\s+)?(?:fitness|PDR):\s*({NUM})", re.I | re.M),
    re.compile(rf"^\s*Simulation of (?:the )?final (?:best )?(?:solution|layout) (?:results|fitness|PDR):\s*({NUM})", re.I | re.M),
]


def final_simulated_pdr(text: str, extra_pattern: str | None = None) -> tuple[float | None, str]:
    patterns = list(VALIDATED_PDR_PATTERNS)
    if extra_pattern:
        patterns.insert(0, re.compile(extra_pattern, re.I | re.M))
    matches = [(m.start(), float(m.group(1)), m.group(0).strip())
               for pattern in patterns for m in pattern.finditer(text)]
    if not matches:
        return None, ""
    _, value, marker = max(matches, key=lambda item: item[0])
    if not 0 <= value <= 1:
        raise ValueError(f"Final verified PDR outside [0,1]: {marker}")
    return value, marker


def actual_pdr(run: 'Run', method: str) -> float | None:
    if run.simulated_pdr is not None:
        return run.simulated_pdr
    if method in ('PSO-Sim', 'Naive-Sim'):
        return run.fitness  # These methods optimize directly with OMNeT++.
    if method == 'Naive-RF' and run.predicted_fitness is not None:
        # Verified against the user's Naive-RF logger semantics: successive
        # "new best fitness" lines are predictions; the FINAL global best
        # fitness is the OMNeT++ result for the selected candidate.
        return run.fitness
    return None  # Do not treat PSO-RF/Hybrid predictions as simulated PDR.


def pdr_fields(reference: 'Run', candidate: 'Run', method: str) -> dict:
    reference_pdr = actual_pdr(reference, 'PSO-Sim')
    candidate_pdr = actual_pdr(candidate, method)
    predicted = (candidate.predicted_fitness if method == 'Naive-RF' else
                 candidate.fitness if method in ('PSO-RF', 'Hybrid') else None)
    return {
        'comparison_logged_fitness': candidate.fitness if candidate.fitness is not None else '',
        'comparison_predicted_best_fitness': predicted if predicted is not None else '',
        'comparison_fitness_source': ('OMNeT++' if method in ('Naive-Sim', 'Naive-RF') else
                                      'RF or hybrid optimizer output; may be predicted'),
        'comparison_actual_pdr': candidate_pdr if candidate_pdr is not None else '',
        'comparison_actual_pdr_source': candidate.simulated_pdr_label if candidate.simulated_pdr is not None
            else ('Final global best fitness (simulation backend)' if method == 'Naive-Sim' else
                  'Final global best fitness (Naive-RF final OMNeT++ run)'
                  if method == 'Naive-RF' and candidate.predicted_fitness is not None else 'MISSING'),
        'pdr_difference_from_pso_sim': (candidate_pdr - reference_pdr)
            if candidate_pdr is not None and reference_pdr is not None else '',
        'prediction_error_actual_minus_logged': (candidate_pdr - predicted)
            if candidate_pdr is not None and predicted is not None else '',
    }


METHODS = [
    ("PSO-RF", "pso_rf"),
    ("Hybrid", "hybrid"),
    ("Naive-Sim", "naive_sim"),
    ("Naive-RF", "naive_rf"),
]


@dataclass
class Run:
    path: Path
    seed: int | None
    area: tuple[float, float] | None
    network: int | None
    sink: np.ndarray | None
    nodes: np.ndarray | None
    relays: np.ndarray
    fitness: float | None
    predicted_fitness: float | None
    simulated_pdr: float | None
    simulated_pdr_label: str


@dataclass
class LogEntry:
    path: Path
    run: Run | None
    error: str = ""


def coordinate_block(lines: list[str], name: str) -> np.ndarray | None:
    """Find an exact section header and parse its subsequent coordinate lines."""
    target = name.lower()
    for index, line in enumerate(lines):
        if line.strip().lower() != target:
            continue
        points = []
        for following in lines[index + 1:]:
            match = COORD_RE.fullmatch(following.strip())
            if match:
                points.append((float(match[1]), float(match[2])))
            elif points:
                break
            elif following.strip():
                break
        return np.asarray(points, dtype=float).reshape((-1, 2))
    return None


def parse_log(path: Path, extra_pattern: str | None = None) -> Run:
    text = path.read_text(encoding="utf-8", errors="replace")
    if "COULD NOT GENERATE RANDOM SOLUTION" in text.upper():
        raise ValueError("random solution generation failed")

    area_match = AREA_RE.search(text)
    # Minimal Naive logs may contain just improvements and final relay positions.
    # In --by-order mode, missing scenario metadata comes from the PSO-Sim log.
    area = (float(area_match[1]), float(area_match[2])) if area_match else None
    if area is not None and (area[0] <= 0 or area[1] <= 0):
        raise ValueError("area must have positive dimensions")

    lines = text.splitlines()
    relays = coordinate_block(lines, "Final global best relays:")
    if relays is None or len(relays) == 0:
        raise ValueError("missing 'Final global best relays:' coordinates")

    nodes = coordinate_block(lines, "Nodes Positions:")
    if nodes is not None and len(nodes) == 0:
        nodes = None

    relay_header = RELAY_COUNT_RE.search(text)
    if relay_header and int(relay_header[1]) != len(relays):
        raise ValueError(f"header says {relay_header[1]} relays, final block has {len(relays)}")

    seed = SEED_RE.search(text)
    network = NETWORK_RE.search(text)
    sink = SINK_RE.search(text)
    fitness = FITNESS_RE.search(text)
    improvements = list(IMPROVEMENT_RE.finditer(text))
    predicted_fitness = float(improvements[-1][1]) if improvements else None
    verified_pdr, verified_label = final_simulated_pdr(text, extra_pattern)
    return Run(
        path=path,
        seed=int(seed[1]) if seed else None,
        area=area,
        network=int(network[1]) if network else None,
        sink=np.array([float(sink[1]), float(sink[2])]) if sink else None,
        nodes=nodes,
        relays=relays,
        fitness=float(fitness[1]) if fitness else None,
        predicted_fitness=predicted_fitness,
        simulated_pdr=verified_pdr,
        simulated_pdr_label=verified_label,
    )


def load_runs(folder: Path, label: str, network_filter: int | None,
              relay_filter: int | None, extra_pattern: str | None = None) -> list[Run]:
    if not folder.is_dir():
        raise SystemExit(f"{label}: not a directory: {folder}")
    paths = sorted(folder.rglob("*.log"))
    if not paths:
        raise SystemExit(f"{label}: no .log files found under {folder}")
    runs = []
    for path in paths:
        try:
            run = parse_log(path, extra_pattern)
        except ValueError as exc:
            print(f"  SKIP {label}: {path.name}: {exc}")
            continue
        if run.area is None:
            print(f"  SKIP {label}: {path.name}: area missing (use --by-order)")
            continue
        if relay_filter is not None and len(run.relays) != relay_filter:
            continue
        if network_filter is not None and run.network is not None and run.network != network_filter:
            continue
        runs.append(run)
    print(f"{label}: loaded {len(runs)} runs from {folder}")
    return runs


def parse_entry(path: Path, extra_pattern: str | None = None) -> LogEntry:
    try:
        return LogEntry(path=path, run=parse_log(path, extra_pattern))
    except ValueError as exc:
        # Keep this position in the sequence so later scenarios do not shift!
        return LogEntry(path=path, run=None, error=str(exc))


def load_ordered(folder: Path, label: str, extra_pattern: str | None = None) -> list[LogEntry]:
    if not folder.is_dir():
        raise SystemExit(f"{label}: not a directory: {folder}")
    # The filenames generated by the logger have ISO timestamps, so sorting
    # by name preserves execution order (not the directory's arbitrary order).
    paths = sorted(folder.rglob("*.log"), key=lambda p: (p.name, str(p)))
    if not paths:
        raise SystemExit(f"{label}: no .log files found under {folder}")
    entries = [parse_entry(path, extra_pattern) for path in paths]
    print(f"{label}: {len(entries)} logs in filename/timestamp order, "
          f"{sum(e.run is not None for e in entries)} with final positions")
    return entries


def load_combined(folder: Path, sequence: list[str], layout: str,
                  extra_pattern: str | None = None) -> dict[str, list[LogEntry]]:
    if not folder.is_dir():
        raise SystemExit(f"not a directory: {folder}")
    paths = sorted(folder.rglob("*.log"), key=lambda p: (p.name, str(p)))
    n_methods = len(sequence)
    if not paths or len(paths) % n_methods:
        raise SystemExit(f"Combined folder: {len(paths)} logs is not divisible by "
                         f"{n_methods} methods. Check --sequence and missing logs.")
    n_scenarios = len(paths) // n_methods
    result = {method: [] for method in sequence}
    if layout == "interleaved":
        for i in range(n_scenarios):
            for j, method in enumerate(sequence):
                result[method].append(parse_entry(paths[i * n_methods + j], extra_pattern))
    else:
        for j, method in enumerate(sequence):
            result[method] = [parse_entry(p, extra_pattern) for p in
                              paths[j * n_scenarios:(j + 1) * n_scenarios]]
    print(f"Combined folder: {n_scenarios} scenarios x {n_methods} methods "
          f"({layout}); verify --sequence reflects your actual run order")
    return result


def same_nodes(a: np.ndarray, b: np.ndarray, atol: float) -> bool:
    if a.shape != b.shape:
        return False
    # Sorting prevents irrelevant ordering differences in the log.
    def ordered(points):
        return points[np.lexsort((points[:, 1], points[:, 0]))]
    return bool(np.allclose(ordered(a), ordered(b), rtol=0, atol=atol))


def is_same_scenario(a: Run, b: Run, atol: float,
                     allow_seed_only: bool) -> bool:
    if len(a.relays) != len(b.relays):
        return False
    if a.area is not None and b.area is not None and not np.allclose(
            a.area, b.area, rtol=0, atol=atol):
        return False
    if a.seed is not None and b.seed is not None and a.seed != b.seed:
        return False
    if a.network is not None and b.network is not None and a.network != b.network:
        return False
    if a.sink is not None and b.sink is not None:
        if not np.allclose(a.sink, b.sink, rtol=0, atol=atol):
            return False
    if a.nodes is not None and b.nodes is not None:
        if not same_nodes(a.nodes, b.nodes, atol):
            return False
    elif not (allow_seed_only and a.seed is not None and a.seed == b.seed):
        # Do not compare runs whose network topology cannot be verified.
        return False
    if a.seed is None or b.seed is None:
        # Identical sensor coordinates required without a common seed.
        return a.nodes is not None and b.nodes is not None
    return True


def ordered_pair_check(a: Run, b: Run, atol: float) -> tuple[str, str]:
    """Verify any metadata present; missing metadata is not a mismatch."""
    if len(a.relays) != len(b.relays):
        return "mismatch", "different relay counts"
    if a.area is not None and b.area is not None and not np.allclose(
            a.area, b.area, rtol=0, atol=atol):
        return "mismatch", "different deployment area"
    if a.seed is not None and b.seed is not None and a.seed != b.seed:
        return "mismatch", "different scenario seeds"
    if a.network is not None and b.network is not None and a.network != b.network:
        return "mismatch", "different network configuration"
    if a.sink is not None and b.sink is not None and not np.allclose(
            a.sink, b.sink, rtol=0, atol=atol):
        return "mismatch", "different sink positions"
    if a.nodes is not None and b.nodes is not None:
        if not same_nodes(a.nodes, b.nodes, atol):
            return "mismatch", "different sensor positions"
        return "verified_nodes", "sensor positions match"
    if a.seed is not None and b.seed is not None:
        return "verified_seed", "scenario seeds match; sensor positions unavailable"
    return "order_only", "paired by log order; scenario metadata unavailable"


def compare_layouts(reference: Run, candidate: Run) -> dict:
    # Rows are reference relays; columns are candidate relays. This avoids
    # spurious distances when algorithms number equivalent relays differently.
    cost = np.linalg.norm(reference.relays[:, None, :] -
                          candidate.relays[None, :, :], axis=2)
    rows, columns = linear_sum_assignment(cost)
    distances = cost[rows, columns]
    diagonal = math.hypot(*reference.area)

    def pair_distances(points: np.ndarray) -> np.ndarray:
        return np.sort(np.array([
            np.linalg.norm(points[i] - points[j])
            for i in range(len(points))
            for j in range(i + 1, len(points))
        ]))

    ref_pairs = pair_distances(reference.relays)
    candidate_pairs = pair_distances(candidate.relays)
    if reference.sink is not None:
        sink_ref = np.sort(np.linalg.norm(reference.relays - reference.sink, axis=1))
        sink_candidate = np.sort(np.linalg.norm(candidate.relays - reference.sink, axis=1))
        sink_profile_mae = float(np.mean(np.abs(sink_ref - sink_candidate)))
    else:
        sink_profile_mae = float("nan")

    return {
        "mean_matched_distance_m": float(np.mean(distances)),
        "rms_matched_distance_m": float(np.sqrt(np.mean(distances ** 2))),
        "max_matched_distance_m": float(np.max(distances)),
        "mean_distance_pct_field_diagonal": float(100 * np.mean(distances) / diagonal),
        "relay_pair_profile_mae_m": float(np.mean(np.abs(ref_pairs - candidate_pairs)))
        if len(ref_pairs) else 0.0,
        "relay_sink_profile_mae_m": sink_profile_mae,
        "relay_assignment": "; ".join(f"ref{r}->candidate{c}" for r, c in zip(rows, columns)),
    }


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    keys = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Saved {path}")


def make_plots(rows: list[dict], out: Path) -> None:
    by_method = defaultdict(list)
    for row in rows:
        if row["method"] != "PSO-Sim":
            by_method[row["method"]].append(row)
    if not by_method:
        return

    fig, ax = plt.subplots(figsize=(11, 5.5))
    for method, method_rows in by_method.items():
        method_rows = sorted(method_rows, key=lambda r: r["scenario_number"])
        ax.plot([r["scenario_number"] for r in method_rows],
                [r["mean_matched_distance_m"] for r in method_rows],
                marker="o", label=f"{method} (n={len(method_rows)})")
    ax.axhline(0, linestyle="--", linewidth=1, label="PSO-Sim reference")
    ax.set(xlabel="Matched scenario number", ylabel="Mean matched relay distance (m)",
           title="Distance from each method to PSO with simulation")
    ax.grid(alpha=0.35)
    ax.legend()
    fig.tight_layout()
    fig.savefig(out / "distance_by_scenario.png", dpi=250)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 5.5))
    names = list(by_method)
    series = [[r["mean_matched_distance_m"] for r in by_method[m]] for m in names]
    ax.boxplot(series, labels=[f"{n}\n(n={len(by_method[n])})" for n in names],
               showmeans=True)
    ax.set(ylabel="Mean matched relay distance (m)",
           title="Layout similarity to PSO with simulation across scenarios")
    ax.grid(axis="y", alpha=0.35)
    fig.tight_layout()
    fig.savefig(out / "distance_boxplot.png", dpi=250)
    plt.close(fig)
    print(f"Saved {out / 'distance_by_scenario.png'}")
    print(f"Saved {out / 'distance_boxplot.png'}")


def compare_by_order(args: argparse.Namespace):
    """Pair log N with log N; never shift subsequent pairs after a bad log."""
    if args.combined_dir is not None:
        if args.pso_sim or any(getattr(args, attr) for _, attr in METHODS):
            raise SystemExit("Use EITHER --combined-dir OR individual method directories")
        if not args.sequence:
            raise SystemExit("--combined-dir requires the exact --sequence of methods")
        if len(set(args.sequence)) != len(args.sequence):
            raise SystemExit("--sequence must not contain duplicate methods")
        if "pso_sim" not in args.sequence or len(args.sequence) < 2:
            raise SystemExit("--sequence must include pso_sim and another method")
        grouped = load_combined(args.combined_dir, args.sequence, args.combined_order,
                                args.actual_pdr_regex)
        reference_entries = grouped["pso_sim"]
        other_entries = {
            label: grouped[attr] for label, attr in METHODS if attr in grouped
        }
    else:
        if args.pso_sim is None:
            raise SystemExit("--pso-sim is required without --combined-dir")
        if not any(getattr(args, attr) for _, attr in METHODS):
            raise SystemExit("Provide at least one comparison directory")
        reference_entries = load_ordered(args.pso_sim, "PSO-Sim", args.actual_pdr_regex)
        other_entries = {
            label: load_ordered(getattr(args, attr), label, args.actual_pdr_regex)
            for label, attr in METHODS if getattr(args, attr) is not None
        }

    n = len(reference_entries)
    if args.expected is not None and n != args.expected:
        raise SystemExit(f"Expected {args.expected} reference logs, found {n}")
    for method, entries in other_entries.items():
        if len(entries) != n:
            raise SystemExit(
                f"Cannot safely pair by order: PSO-Sim has {n} files, "
                f"but {method} has {len(entries)}. An extra/missing log "
                "can shift every later pair. Check your directories."
            )

    print("\nPAIRING BY SORTED FILENAME/TIMESTAMP. This assumes every method "
          "ran scenarios in exactly the same order. Missing metadata cannot "
          "independently confirm the scenario identity.\n")

    reference_runs = []
    result_rows = []
    pairing_rows = []
    selected = defaultdict(dict)

    for index, reference_entry in enumerate(reference_entries, 1):
        reference = reference_entry.run
        if reference is None or reference.area is None:
            print(f"  SKIP scenario {index}: invalid PSO-Sim reference: "
                  f"{reference_entry.error or 'missing area'}")
            for method, candidates in other_entries.items():
                pairing_rows.append({
                    "scenario_number": index, "method": method,
                    "pso_sim_log": str(reference_entry.path),
                    "comparison_log": str(candidates[index - 1].path),
                    "status": "invalid_reference",
                    "detail": reference_entry.error or "PSO-Sim reference has no area",
                })
            continue

        if args.network is not None:
            if reference.network is None:
                raise SystemExit("--network requires Network Configuration ID "
                                 "in PSO-Sim reference logs")
            if reference.network != args.network:
                continue
        if args.relays is not None and len(reference.relays) != args.relays:
            continue

        reference_runs.append(reference)
        base = {
            "scenario_number": index,
            "seed": reference.seed if reference.seed is not None else "",
            "network": reference.network if reference.network is not None else "",
            "area_width_m": reference.area[0],
            "area_height_m": reference.area[1],
            "sensor_count": len(reference.nodes) if reference.nodes is not None else "",
            "relay_count": len(reference.relays),
            "pso_sim_log": str(reference.path),
            "pso_sim_pdr": actual_pdr(reference, "PSO-Sim") if actual_pdr(reference, "PSO-Sim") is not None else "",
        }

        for method, candidates in other_entries.items():
            candidate_entry = candidates[index - 1]
            candidate = candidate_entry.run
            status, detail = (
                ("invalid_log", candidate_entry.error)
                if candidate is None else
                ordered_pair_check(reference, candidate, args.tolerance)
            )
            pairing_rows.append({
                "scenario_number": index,
                "method": method,
                "pso_sim_log": str(reference.path),
                "comparison_log": str(candidate_entry.path),
                "status": status, "detail": detail,
            })
            if status in ("invalid_log", "mismatch"):
                print(f"  SKIP scenario {index} {method}: {detail} "
                      f"({candidate_entry.path.name})")
                continue
            if status == "order_only":
                print(f"  NOTE scenario {index} {method}: order-only pairing "
                      "(no common scenario identifier)")

            # Naive logs often omit area/sink/seed/nodes. Fill only the
            # metadata needed to compute geometry, from the paired reference.
            # This does NOT constitute independent verification of pairing.
            candidate = replace(
                candidate,
                area=candidate.area if candidate.area is not None else reference.area,
                sink=candidate.sink if candidate.sink is not None else reference.sink,
                seed=candidate.seed if candidate.seed is not None else reference.seed,
                network=candidate.network if candidate.network is not None else reference.network,
            )
            selected[method][index] = candidate
            metrics = compare_layouts(reference, candidate)
            result_rows.append({
                **base, "method": method, "comparison_log": str(candidate.path),
                "pairing_status": status,
                **pdr_fields(reference, candidate, method),
                **metrics,
            })

    return reference_runs, result_rows, selected, pairing_rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--pso-sim", type=Path,
                        help="Folder containing PSO evaluated with OMNeT++ logs")
    parser.add_argument("--pso-rf", "--pso-surrogate", dest="pso_rf", type=Path)
    parser.add_argument("--hybrid", type=Path)
    parser.add_argument("--naive-sim", type=Path)
    parser.add_argument("--naive-rf", "--naive-surrogate", dest="naive_rf", type=Path)
    parser.add_argument("--out", type=Path, default=Path("layout_comparison"))
    parser.add_argument("--network", type=int, help="Keep only this Network Configuration ID")
    parser.add_argument("--relays", type=int, help="Keep only runs with this relay count")
    parser.add_argument("--tolerance", type=float, default=0.02,
                        help="Coordinate tolerance for topology matching (m; default: 0.02)")
    parser.add_argument("--allow-seed-only", action="store_true",
                        help="Permit matching without logged sensor coordinates if seeds agree")
    parser.add_argument("--by-order", action="store_true",
                        help="Pair sorted log N with log N; works with minimal Naive logs")
    parser.add_argument("--combined-dir", type=Path,
                        help="All methods logged in a single folder; requires --sequence")
    parser.add_argument("--sequence", nargs="+",
                        choices=["pso_sim", "pso_rf", "hybrid", "naive_sim", "naive_rf"],
                        help="Exact method execution order in --combined-dir")
    parser.add_argument("--combined-order", choices=["interleaved", "grouped"],
                        default="interleaved",
                        help="One scenario then all methods, or all scenarios per method")
    parser.add_argument("--expected", type=int,
                        help="Require exactly N logs per method (e.g. --expected 12)")
    parser.add_argument("--actual-pdr-regex", type=str,
                        help="Optional Python regex for explicit FINAL OMNeT++ verification PDR; "
                             "must contain one capturing group for the numeric PDR. "
                             "Do not match intermediate simulations.")
    args = parser.parse_args()

    if args.tolerance <= 0:
        parser.error("--tolerance must be positive")
    if args.actual_pdr_regex:
        try:
            regex = re.compile(args.actual_pdr_regex)
        except re.error as exc:
            parser.error(f"invalid --actual-pdr-regex: {exc}")
        if regex.groups != 1:
            parser.error("--actual-pdr-regex requires exactly one capturing group")
    if args.expected is not None and args.expected < 1:
        parser.error("--expected must be positive")
    if args.combined_dir is not None and not args.sequence:
        parser.error("--combined-dir requires --sequence")
    if args.combined_dir is None and args.sequence:
        parser.error("--sequence only applies to --combined-dir")
    if args.combined_dir is None and args.pso_sim is None:
        parser.error("provide --pso-sim or --combined-dir")
    if args.combined_dir is None and not any(getattr(args, attr) for _, attr in METHODS):
        parser.error("provide at least one comparison directory, e.g. --pso-rf")

    if args.combined_dir is not None or args.by_order:
        reference_runs, result_rows, selected, pairing_rows = compare_by_order(args)
    else:
        reference_runs = load_runs(args.pso_sim, "PSO-Sim", args.network, args.relays,
                                   args.actual_pdr_regex)
        other_runs = {
            label: load_runs(getattr(args, arg), label, args.network, args.relays,
                             args.actual_pdr_regex)
            for label, arg in METHODS if getattr(args, arg) is not None
        }
        if not reference_runs:
            raise SystemExit("No usable PSO-Sim reference runs.")
        if args.expected is not None and len(reference_runs) != args.expected:
            raise SystemExit(f"Expected {args.expected} reference logs, "
                             f"found {len(reference_runs)}")

        reference_runs.sort(key=lambda r: (r.seed is None, r.seed or 0, r.path.name))
        result_rows = []
        selected = defaultdict(dict)
        pairing_rows = []
        used = defaultdict(set)
        for scenario_number, reference in enumerate(reference_runs, 1):
            base = {
                "scenario_number": scenario_number,
                "seed": reference.seed if reference.seed is not None else "",
                "network": reference.network if reference.network is not None else "",
                "area_width_m": reference.area[0],
                "area_height_m": reference.area[1],
                "sensor_count": len(reference.nodes) if reference.nodes is not None else "",
                "relay_count": len(reference.relays),
                "pso_sim_log": str(reference.path),
                "pso_sim_pdr": actual_pdr(reference, "PSO-Sim") if actual_pdr(reference, "PSO-Sim") is not None else "",
            }
            for method, candidates in other_runs.items():
                matches = [run for run in candidates if is_same_scenario(
                    reference, run, args.tolerance, args.allow_seed_only)]
                if len(matches) != 1:
                    print(f"  WARNING scenario #{scenario_number} seed={reference.seed}: "
                          f"{method} has {len(matches)} matching logs (need exactly one). "
                          "Check seed, sensor positions, network, or filter directories.")
                    continue
                run = matches[0]
                if run.path in used[method]:
                    print(f"  WARNING {run.path} matched multiple reference runs; "
                          "ambiguous experimental configuration. Skipping duplicate.")
                    continue
                used[method].add(run.path)
                selected[method][scenario_number] = run
                metrics = compare_layouts(reference, run)
                result_rows.append({
                    **base, "method": method, "comparison_log": str(run.path),
                    **pdr_fields(reference, run, method),
                    **metrics,
                })

    if not result_rows:
        raise SystemExit("No usable pairs. Inspect pairing warnings and input logs.")

    args.out.mkdir(parents=True, exist_ok=True)
    if pairing_rows:
        write_csv(args.out / "log_pairing.csv", pairing_rows)
    write_csv(args.out / "per_scenario_distances.csv", result_rows)
    summary = []
    for method, _ in METHODS:
        subset = [r for r in result_rows if r["method"] == method]
        if not subset:
            continue
        distances = np.array([r["mean_matched_distance_m"] for r in subset])
        gaps = [r["pdr_difference_from_pso_sim"] for r in subset
                if isinstance(r["pdr_difference_from_pso_sim"], (int, float))]
        summary.append({
            "method": method, "paired_scenarios": len(subset),
            "mean_distance_m": float(distances.mean()),
            "std_distance_m": float(distances.std(ddof=1)) if len(distances) > 1 else 0.0,
            "median_distance_m": float(np.median(distances)),
            "min_distance_m": float(distances.min()),
            "max_distance_m": float(distances.max()),
            "mean_pdr_difference_from_pso_sim": float(np.mean(gaps)) if gaps else "",
            "actual_pdr_count": len([r for r in subset if isinstance(r["comparison_actual_pdr"], (int, float))]),
            "mean_actual_pdr": float(np.mean([r["comparison_actual_pdr"] for r in subset
                if isinstance(r["comparison_actual_pdr"], (int, float))]))
                if any(isinstance(r["comparison_actual_pdr"], (int, float)) for r in subset) else "",
            "mean_prediction_error_actual_minus_logged": float(np.mean([
                r["prediction_error_actual_minus_logged"] for r in subset
                if isinstance(r["prediction_error_actual_minus_logged"], (int, float))]))
                if any(isinstance(r["prediction_error_actual_minus_logged"], (int, float)) for r in subset) else "",
        })
    write_csv(args.out / "summary.csv", summary)
    make_plots(result_rows, args.out)

    # Plot final verified PDR across paired scenarios; no predictions allowed.
    fig, ax = plt.subplots(figsize=(10, 5.5))
    per_method = defaultdict(dict)
    reference_pdr = {}
    for row in result_rows:
        if isinstance(row["pso_sim_pdr"], (int, float)):
            reference_pdr[row["scenario_number"]] = row["pso_sim_pdr"]
        if isinstance(row["comparison_actual_pdr"], (int, float)):
            per_method[row["method"]][row["scenario_number"]] = row["comparison_actual_pdr"]
    if reference_pdr:
        indices = sorted(reference_pdr)
        ax.plot(indices, [reference_pdr[i] for i in indices], marker="o", label="PSO-Sim")
        for label, _ in METHODS:
            if per_method[label]:
                xs = sorted(per_method[label])
                ax.plot(xs, [per_method[label][i] for i in xs], marker="o", label=label)
        ax.set(xlabel="Scenario number (order-paired)", ylabel="Final verified OMNeT++ PDR",
               title="Actual network performance of final relay layouts")
        ax.grid(alpha=0.3)
        ax.legend()
        fig.tight_layout()
        fig.savefig(args.out / "actual_pdr_by_scenario.png", dpi=250)
        print(f"Saved {args.out / 'actual_pdr_by_scenario.png'}")
    plt.close(fig)

    # An additional comparison directly tests the observation that Naive-RF
    # and Naive-Sim tend to select similar relay placements.
    if "Naive-Sim" in selected and "Naive-RF" in selected:
        naive_rows = []
        for scenario_number in sorted(set(selected["Naive-Sim"]) & set(selected["Naive-RF"])):
            naive_sim = selected["Naive-Sim"][scenario_number]
            naive_rf = selected["Naive-RF"][scenario_number]
            metrics = compare_layouts(naive_sim, naive_rf)
            naive_rows.append({
                "scenario_number": scenario_number,
                "seed": naive_sim.seed if naive_sim.seed is not None else "",
                "naive_sim_log": str(naive_sim.path),
                "naive_rf_log": str(naive_rf.path),
                "naive_sim_pdr": actual_pdr(naive_sim, "Naive-Sim") if actual_pdr(naive_sim, "Naive-Sim") is not None else "",
                "naive_rf_logged_fitness": naive_rf.fitness if naive_rf.fitness is not None else "",
                "naive_rf_predicted_best": naive_rf.predicted_fitness if naive_rf.predicted_fitness is not None else "",
                "naive_rf_actual_pdr": actual_pdr(naive_rf, "Naive-RF") if actual_pdr(naive_rf, "Naive-RF") is not None else "",
                "naive_rf_minus_naive_sim_actual_pdr": (
                    actual_pdr(naive_rf, "Naive-RF") - actual_pdr(naive_sim, "Naive-Sim"))
                    if actual_pdr(naive_rf, "Naive-RF") is not None
                    and actual_pdr(naive_sim, "Naive-Sim") is not None else "",
                **metrics,
            })
        write_csv(args.out / "naive_rf_vs_naive_sim.csv", naive_rows)
        if naive_rows:
            print("Naive-RF vs Naive-Sim mean matched distance: "
                  f"{np.mean([r['mean_matched_distance_m'] for r in naive_rows]):.2f} m "
                  f"across {len(naive_rows)} paired scenarios (check log_pairing.csv)")

    print("\nSummary (reference: PSO-Sim):")
    for row in summary:
        print(f"  {row['method']:12s} n={row['paired_scenarios']:2d}  "
              f"mean={row['mean_distance_m']:8.2f} m  "
              f"sd={row['std_distance_m']:7.2f} m  "
              f"PDR gap={row['mean_pdr_difference_from_pso_sim']}")
    print("PDR differences use FINAL OMNeT++ verification results, never RF predictions.")
    print("Naive-RF format: final global best fitness = final simulated PDR; "
          "last new best fitness = RF prediction.")
    for row in summary:
        if row["actual_pdr_count"] < row["paired_scenarios"]:
            print(f"  MISSING final simulation PDR for "
                  f"{row['method']}: {row['paired_scenarios'] - row['actual_pdr_count']} "
                  f"of {row['paired_scenarios']} paired logs. "
                  "If your log uses another label, pass --actual-pdr-regex.")
    if any(row["paired_scenarios"] != len(reference_runs) for row in summary):
        print("WARNING: at least one method is missing verified scenario pairs. "
              "Inspect warnings above before drawing conclusions.")


if __name__ == "__main__":
    main()