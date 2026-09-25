#!/usr/bin/env python3
"""Build corrected PSO-vs-Naive tables from detailed optimizer .log files.

Phase 3 protocol (per relay count):
    12 paired PSO/Naive runs at high relay/high node power;
    12 paired PSO/Naive runs at high relay/mid node power.
Both blocks use the same 12 scenario seeds. Logs must be timestamp-ordered
by filename and each PSO log must be followed by its Naive log.

The fair PSO value is the best fitness in its FIRST 400 evaluations, not
its final value after an optional 21st generation (420 evaluations).
"""

import argparse
import re
from pathlib import Path
from math import sqrt

import pandas as pd


EVALUATION_BUDGET = 400
PHASE3_SEEDS = 12
PHASE3_RELAYS = (2, 3, 4, 6)
# Two-sided 95% Student t critical value for 12 paired observations (df=11).
T_CRIT_95_DF11 = 2.200985160
EPS = 1e-9

# Phase 2, unchanged from your prior script.
NETWORK_CONFIGS = {
    1: (0.00224, 0.00224),
    2: (0.00224, 0.001),
    3: (0.00224, 0.000316),
    4: (0.001, 0.00224),
    5: (0.001, 0.001),
    6: (0.001, 0.000316),
    7: (0.000316, 0.00224),
    8: (0.000316, 0.001),
    9: (0.000316, 0.000316),
}

PHASE3_POWERS = {
    "HH": (0.00224, 0.00224),  # relay high, node high
    "HM": (0.00224, 0.001),    # relay high, node mid
}


def natural_key(path):
    return [
        int(part) if part.isdigit() else part.lower()
        for part in re.split(r"(\d+)", path.name)
    ]


def extract_int(pattern, text, default=None):
    match = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
    return int(match.group(1)) if match else default


def extract_float(pattern, text, default=None):
    match = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
    return float(match.group(1)) if match else default


def method_of(text):
    if "PSO EXECUTION" in text or re.search(r"^Particles:\s*\d+", text, re.M):
        return "PSO"
    if (
        "NAIVE EXECUTION" in text.upper()
        or re.search(r"new best fitness:", text, re.I)
        or re.search(r"COULD NOT GENERATE RANDOM SOLUTION", text, re.I)
    ):
        return "Naive"
    return None


def metadata_of(text):
    area_match = re.search(
        r"^Area:\s*([\d.]+)\s*x\s*([\d.]+)", text, re.I | re.M
    )
    return {
        "seed": extract_int(r"^Seed:\s*(\d+)", text),
        "relays": extract_int(r"^Relays:\s*(\d+)", text),
        "network_config": extract_int(r"^Network Configuration:\s*(\d+)", text),
        "width": float(area_match.group(1)) if area_match else None,
        "height": float(area_match.group(2)) if area_match else None,
    }


def parse_pso(path, text):
    values = [
        float(value)
        for value in re.findall(
            r"^Resulting Fitness:\s*([-+\d.eE]+)", text, re.I | re.M
        )
    ]
    if len(values) < EVALUATION_BUDGET:
        raise ValueError(
            f"PSO log {path.name}: only {len(values)} evaluations; "
            f"cannot compute the best at {EVALUATION_BUDGET}."
        )

    best_400 = max(values[:EVALUATION_BUDGET])
    reported_final = extract_float(
        r"^Final global best fitness:\s*([-+\d.eE]+)", text
    )
    final = max(values) if reported_final is None else reported_final
    if abs(final - max(values)) > 1e-5:
        raise ValueError(
            f"PSO log {path.name}: final fitness {final} differs from "
            f"the maximum logged fitness {max(values)}."
        )

    return {
        "file": path.name,
        "meta": metadata_of(text),
        "best_400": best_400,
        "final": final,
        "extra_gain": max(0.0, final - best_400),
        "evaluations": len(values),
    }


def parse_naive(path, text):
    reported_final = extract_float(
        r"^Final global best fitness:\s*([-+\d.eE]+)", text
    )
    best_values = [
        float(value)
        for value in re.findall(r"new best fitness:\s*([-+\d.eE]+)", text, re.I)
    ]
    # If rejection sampling stops early, retain the last feasible best.
    # A zero when no solution exists is a search-failure placeholder, NOT PDR=0.
    fitness = reported_final
    if fitness is None:
        fitness = max(best_values, default=0.0)

    failed = bool(re.search(r"COULD NOT GENERATE RANDOM SOLUTION", text, re.I))
    no_solution = reported_final is None and not best_values
    return {
        "file": path.name,
        "meta": metadata_of(text),
        "fitness": fitness,
        "failed": failed or no_solution,
        "no_solution": no_solution,
    }


def read_pairs(folder, pattern, strict=False):
    files = sorted(folder.glob(pattern), key=natural_key)
    if not files:
        raise ValueError(f"No files matching {pattern!r} in {folder}")

    # Read/classify once; ignore unrelated logs, but not broken pairs.
    candidates = []
    for path in files:
        text = path.read_text(encoding="utf-8", errors="replace")
        method = method_of(text)
        if method is None:
            print(f"WARNING: skipping unrecognized file {path.name}")
        else:
            candidates.append((path, text, method))

    pairs = []
    i = 0
    while i < len(candidates):
        path, text, method = candidates[i]
        if method != "PSO":
            message = f"Orphan Naive log: {path.name}"
            if strict:
                raise ValueError(message)
            print(f"WARNING: {message}")
            i += 1
            continue
        if i + 1 >= len(candidates) or candidates[i + 1][2] != "Naive":
            message = f"Missing following Naive log for PSO {path.name}"
            if strict:
                raise ValueError(message)
            print(f"WARNING: {message}")
            i += 1
            continue

        naive_path, naive_text, _ = candidates[i + 1]
        pso = parse_pso(path, text)
        naive = parse_naive(naive_path, naive_text)
        for field in ("seed", "relays", "width", "height", "network_config"):
            a, b = pso["meta"][field], naive["meta"][field]
            if a is not None and b is not None and a != b:
                raise ValueError(
                    f"Mismatched {field} in pair {path.name} / {naive_path.name}: "
                    f"{a} vs {b}"
                )

        meta = pso["meta"]
        if meta["seed"] is None or meta["relays"] is None:
            raise ValueError(f"Missing seed or relay count in {path.name}")
        pairs.append({
            "pair_index": len(pairs) + 1,
            "seed": meta["seed"],
            "relays": meta["relays"],
            "width": meta["width"],
            "height": meta["height"],
            "network_config": meta["network_config"],
            "pso_400": pso["best_400"],
            "pso_final": pso["final"],
            "pso_extra_20_gain": pso["extra_gain"],
            "pso_evaluations": pso["evaluations"],
            "naive_400": naive["fitness"],
            "naive_failed": naive["failed"],
            "naive_no_solution": naive["no_solution"],
            "delta": pso["best_400"] - naive["fitness"],
            "pso_file": pso["file"],
            "naive_file": naive["file"],
        })
        i += 2

    if not pairs:
        raise ValueError("No PSO/Naive pairs were found")
    return pd.DataFrame(pairs)


def build_phase1(df, output_dir):
    df = df.copy()
    df["area"] = df["width"].astype(int)
    table = df.pivot_table(
        index="relays", columns="area", values="delta", aggfunc="mean"
    ).sort_index().sort_index(axis=1)
    counts = df.groupby(["relays", "area"]).size().unstack()
    print("\nPHASE 1: mean PSO@400 - Naive@400\n")
    print(table.to_string(float_format=lambda x: f"{x:+.4f}"))
    print("\nNumber of pairs:\n", counts.to_string())
    df.to_csv(output_dir / "phase1_paired_results.csv", index=False)
    table.to_csv(output_dir / "phase1_mean_delta_table.csv")
    counts.to_csv(output_dir / "phase1_seed_count_table.csv")


def build_phase2(df, output_dir):
    df = df.copy()
    if df["network_config"].isna().any():
        raise ValueError("Phase 2 requires Network Configuration in PSO logs")
    df["network_config"] = df["network_config"].astype(int)
    unknown = set(df["network_config"]) - set(NETWORK_CONFIGS)
    if unknown:
        raise ValueError(f"Unknown Phase 2 network configurations: {unknown}")
    df["relay_power"] = df["network_config"].map(lambda n: NETWORK_CONFIGS[n][0])
    df["node_power"] = df["network_config"].map(lambda n: NETWORK_CONFIGS[n][1])
    summary = df.groupby(
        ["relays", "relay_power", "node_power"], as_index=False
    )["delta"].mean()
    combined = summary.pivot(
        index=["relays", "relay_power"], columns="node_power", values="delta"
    ).sort_index(level=[0, 1], ascending=[True, False]).sort_index(axis=1, ascending=False)
    print("\nPHASE 2: mean PSO@400 - Naive@400\n")
    print(combined.to_string(float_format=lambda x: f"{x:+.4f}"))
    df.to_csv(output_dir / "phase2_paired_results.csv", index=False)
    summary.to_csv(output_dir / "phase2_mean_delta.csv", index=False)
    combined.to_csv(output_dir / "phase2_combined_power_table.csv")
    for r in sorted(summary["relays"].unique()):
        combined.loc[r].to_csv(output_dir / f"phase2_{r}_relays.csv")


def build_phase3(df, output_dir):
    """Assign power using the order of 12 pairs within EACH relay count."""
    df = df.copy()
    actual = set(df["relays"].unique())
    if actual != set(PHASE3_RELAYS):
        raise ValueError(
            f"Phase 3 expects relays {PHASE3_RELAYS}; found {sorted(actual)}. "
            "Check that you selected the complete Phase 3 log folder."
        )

    pieces = []
    for relays in PHASE3_RELAYS:
        # read_pairs() preserves chronological filename ordering.
        group = df.loc[df["relays"] == relays].sort_values("pair_index").copy()
        expected = PHASE3_SEEDS * len(PHASE3_POWERS)
        if len(group) != expected:
            raise ValueError(
                f"{relays} relays: expected {expected} PSO/Naive pairs "
                f"(12 HH then 12 HM), found {len(group)}. "
                "Do not infer power labels from an incomplete sequence."
            )

        hh_seeds = group.iloc[:PHASE3_SEEDS]["seed"].tolist()
        hm_seeds = group.iloc[PHASE3_SEEDS:]["seed"].tolist()
        if len(set(hh_seeds)) != PHASE3_SEEDS or len(set(hm_seeds)) != PHASE3_SEEDS:
            raise ValueError(f"{relays} relays: repeated seed within a power block")
        if set(hh_seeds) != set(hm_seeds):
            raise ValueError(
                f"{relays} relays: HH and HM do not have the same 12 seeds. "
                "Check the log order or missing files."
            )

        power_labels = ["HH"] * PHASE3_SEEDS + ["HM"] * PHASE3_SEEDS
        group["power"] = power_labels
        group["relay_power"] = group["power"].map(lambda p: PHASE3_POWERS[p][0])
        group["node_power"] = group["power"].map(lambda p: PHASE3_POWERS[p][1])
        group["result_400"] = group["delta"].map(
            lambda d: "WIN" if d > EPS else ("LOSS" if d < -EPS else "TIE")
        )
        pieces.append(group)

    paired = pd.concat(pieces, ignore_index=True)
    paired = paired.sort_values(["relays", "power", "pair_index"])

    # Validate 96 unique scenario/power pairs; seeds intentionally repeat across powers.
    if paired.duplicated(["relays", "power", "seed"]).any():
        raise ValueError("Duplicate (relays, power, seed) in Phase 3")

    summary_rows = []
    for relays in PHASE3_RELAYS:
        for power in ("HH", "HM"):
            group = paired.loc[(paired["relays"] == relays) & (paired["power"] == power)]
            n = len(group)
            if n != PHASE3_SEEDS:
                raise AssertionError(f"Expected {PHASE3_SEEDS} seeds, got {n}")
            delta = group["delta"]
            mean_delta = delta.mean()
            sd_delta = delta.std(ddof=1)
            ci_margin = T_CRIT_95_DF11 * sd_delta / sqrt(n)
            summary_rows.append({
                "relays": relays,
                "power": power,
                "relay_power": PHASE3_POWERS[power][0],
                "node_power": PHASE3_POWERS[power][1],
                "n": n,
                "mean_pso_400": group["pso_400"].mean(),
                "mean_naive_400": group["naive_400"].mean(),
                "mean_delta": mean_delta,
                "median_delta": delta.median(),
                "sd_delta": sd_delta,
                "ci95_low": mean_delta - ci_margin,
                "ci95_high": mean_delta + ci_margin,
                "wins": int((delta > EPS).sum()),
                "ties": int((delta.abs() <= EPS).sum()),
                "losses": int((delta < -EPS).sum()),
                "naive_failures": int(group["naive_failed"].sum()),
                "naive_no_solution": int(group["naive_no_solution"].sum()),
                "pso_extra_20_improvements": int((group["pso_extra_20_gain"] > EPS).sum()),
                "mean_extra_20_gain": group["pso_extra_20_gain"].mean(),
            })

    stats = pd.DataFrame(summary_rows)
    final_table = stats.pivot(
        index="relays", columns="power", values="mean_delta"
    )[["HH", "HM"]]
    pdr_table = stats.pivot(
        index="relays", columns="power", values=["mean_pso_400", "mean_naive_400"]
    )

    print("\nPHASE 3: 12 fresh paired seeds per cell, 400 evaluations each")
    print("HH = relay 0.00224 W / node 0.00224 W")
    print("HM = relay 0.00224 W / node 0.001 W")
    print("\nFINAL TABLE: mean (PSO@400 - Naive@400)\n")
    print(final_table.to_string(float_format=lambda x: f"{x:+.6f}"))
    print("\nPAIRED-SEED STATISTICS\n")
    display = stats[[
        "relays", "power", "n", "mean_pso_400", "mean_naive_400",
        "mean_delta", "median_delta", "ci95_low", "ci95_high",
        "wins", "ties", "losses", "naive_failures"
    ]]
    print(display.to_string(index=False, float_format=lambda x: f"{x:+.6f}"))

    if stats["naive_failures"].sum():
        print("\nWARNING: Naive feasibility failures occurred; inspect the paired CSV.")
        print("An absent feasible layout is NOT a measured PDR of zero.")
    extra = int(stats["pso_extra_20_improvements"].sum())
    print(f"\nPSO runs improved by evaluations 401+: {extra} (excluded from the final table)")

    paired.to_csv(output_dir / "phase3_paired_results.csv", index=False)
    stats.to_csv(output_dir / "phase3_statistics.csv", index=False)
    final_table.to_csv(output_dir / "phase3_final_table.csv")
    pdr_table.to_csv(output_dir / "phase3_mean_pdr_table.csv")
    print(f"\nSaved four Phase 3 CSVs to: {output_dir}")


def main():
    parser = argparse.ArgumentParser(
        description="Build fair PSO@400 vs Naive@400 tables from detailed .log files"
    )
    parser.add_argument("folder", type=Path, help="Folder containing chronological PSO/Naive .logs")
    parser.add_argument("phase", choices=["phase1", "phase2", "phase3"])
    parser.add_argument("--pattern", default="*.log", help="Log file glob (default: *.log)")
    args = parser.parse_args()

    if not args.folder.is_dir():
        parser.error(f"No such directory: {args.folder}")
    df = read_pairs(args.folder, args.pattern, strict=(args.phase == "phase3"))
    output_dir = args.folder / "corrected_parsed_tables"
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Parsed {len(df)} PSO/Naive pairs")
    print(f"PSO runs improved after evaluation 400: {(df['pso_extra_20_gain'] > EPS).sum()}")
    if args.phase == "phase1":
        build_phase1(df, output_dir)
    elif args.phase == "phase2":
        build_phase2(df, output_dir)
    else:
        build_phase3(df, output_dir)


if __name__ == "__main__":
    main()