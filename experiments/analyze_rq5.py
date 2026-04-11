#!/usr/bin/env python3
"""RQ5 Analysis: Coverage map experiment charts and statistics."""
import argparse
import csv
import sys
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

try:
    from scipy import stats as scipy_stats
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

BRAIN_ORDER = ["Subsumption", "Coverage", "Q-Learning"]
COLORS = {"Subsumption": "#4C72B0", "Coverage": "#C44E52", "Q-Learning": "#55A868"}
_BRAIN_ALIASES = {
    "subsumption": "Subsumption", "coverage": "Coverage",
    "potential_field": "Potential Field",
    "qlearning": "Q-Learning", "q_learning": "Q-Learning",
}


def _canon(raw):
    return _BRAIN_ALIASES.get(raw.strip().lower().replace("-", "_").replace(" ", "_"), raw.strip())


def _apply_style():
    for s in ("seaborn-v0_8-whitegrid", "seaborn-whitegrid", "ggplot"):
        try:
            plt.style.use(s); return
        except OSError:
            continue


def _style_ax(ax, title, ylabel, xlabel=None):
    ax.set_title(title, fontsize=14, pad=12)
    ax.set_ylabel(ylabel, fontsize=12)
    if xlabel:
        ax.set_xlabel(xlabel, fontsize=12)
    ax.tick_params(labelsize=11)
    ax.grid(True, linestyle="--", color="lightgray", alpha=0.7)


def _savefig(fig, path):
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def read_csv(path):
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            row["brain_type"] = _canon(row["brain_type"])
            for k in ("seed", "frames", "dirt_collected", "cat_freeze_count", "battery_depletions"):
                if k in row:
                    try: row[k] = int(row[k])
                    except: row[k] = 0
            for k in ("collection_rate", "final_coverage"):
                if k in row:
                    try: row[k] = float(row[k])
                    except: row[k] = 0.0
            rows.append(row)
    return rows


def read_timeline_csv(path):
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            row["brain_type"] = _canon(row["brain_type"])
            try: row["frame"] = int(row["frame"])
            except: row["frame"] = 0
            try: row["coverage_pct"] = float(row["coverage_pct"])
            except: row["coverage_pct"] = 0.0
            try: row["seed"] = int(row["seed"])
            except: row["seed"] = 0
            rows.append(row)
    return rows


def chart_coverage_comparison(rows, out_dir):
    """Grouped bar: dirt collected per brain, grouped by duration."""
    durations = ["short", "long"]
    brains = [b for b in BRAIN_ORDER if any(r["brain_type"] == b for r in rows)]

    fig, ax = plt.subplots(figsize=(10, 6))
    x = np.arange(len(durations))
    width = 0.25
    for i, brain in enumerate(brains):
        means = []
        stds = []
        for dt in durations:
            vals = [r["dirt_collected"] for r in rows
                    if r["brain_type"] == brain and r["duration_type"] == dt]
            means.append(np.mean(vals) if vals else 0)
            stds.append(np.std(vals, ddof=1) if len(vals) > 1 else 0)
        c = COLORS.get(brain, "#999")
        ax.bar(x + i * width, means, width, yerr=stds, capsize=5,
               label=brain, color=c, edgecolor="white")

    ax.set_xticks(x + width)
    ax.set_xticklabels(["Short (1500 frames)", "Long (5000 frames)"])
    ax.legend(fontsize=11)
    _style_ax(ax, "Cleaning Performance: Memory vs Memoryless",
              "Mean Dirt Collected")
    p = Path(out_dir) / "bar_coverage_comparison.png"
    _savefig(fig, p)
    return str(p)


def chart_coverage_timeline(timeline_rows, out_dir):
    """Line chart: coverage % over time for coverage brain (long runs only)."""
    data = defaultdict(lambda: defaultdict(list))
    for r in timeline_rows:
        if r["duration_type"] == "long":
            data[r["brain_type"]][r["frame"]].append(r["coverage_pct"])

    fig, ax = plt.subplots(figsize=(10, 6))
    for brain in BRAIN_ORDER:
        if brain not in data:
            continue
        frames = sorted(data[brain].keys())
        means = [np.mean(data[brain][f]) for f in frames]
        if all(m == 0 for m in means):
            continue  # Skip brains without coverage tracking
        c = COLORS.get(brain, "#999")
        ax.plot(frames, [m * 100 for m in means], "-", color=c, linewidth=2, label=brain)
    ax.legend(fontsize=11)
    _style_ax(ax, "Coverage Percentage Over Time (Long Runs)",
              "Coverage (%)", "Frame")
    p = Path(out_dir) / "line_coverage_over_time.png"
    _savefig(fig, p)
    return str(p)


def chart_coverage_safety(rows, out_dir):
    """Bar chart: safety metrics per brain and duration."""
    durations = ["short", "long"]
    brains = [b for b in BRAIN_ORDER if any(r["brain_type"] == b for r in rows)]

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    for ax, metric, title, ylabel in [
        (axes[0], "cat_freeze_count", "Cat Freezes: Memory vs Memoryless",
         "Mean Cat Freeze Events"),
        (axes[1], "battery_depletions", "Battery Depletions: Memory vs Memoryless",
         "Mean Battery Depletions"),
    ]:
        x = np.arange(len(durations))
        width = 0.25
        for i, brain in enumerate(brains):
            means = []
            for dt in durations:
                vals = [r[metric] for r in rows
                        if r["brain_type"] == brain and r["duration_type"] == dt]
                means.append(np.mean(vals) if vals else 0)
            c = COLORS.get(brain, "#999")
            ax.bar(x + i * width, means, width, label=brain, color=c, edgecolor="white")
        ax.set_xticks(x + width)
        ax.set_xticklabels(["Short", "Long"])
        ax.legend(fontsize=10)
        _style_ax(ax, title, ylabel)

    p = Path(out_dir) / "bar_coverage_safety.png"
    _savefig(fig, p)
    return str(p)


def generate_stats(rows, out_dir):
    lines = ["=" * 70, "RQ5: COVERAGE MAP - STATISTICS", "=" * 70]
    brains = [b for b in BRAIN_ORDER if any(r["brain_type"] == b for r in rows)]
    durations = ["short", "long"]

    for metric in ("dirt_collected", "final_coverage", "cat_freeze_count", "battery_depletions"):
        lines.append(f"\n--- {metric} ---")
        # Use 4 decimal places for coverage to avoid rounding ambiguity
        fmt = ".4f" if metric == "final_coverage" else ".2f"
        for dt in durations:
            lines.append(f"  [{dt}]")
            for brain in brains:
                vals = [r[metric] for r in rows
                        if r["brain_type"] == brain and r["duration_type"] == dt]
                if vals:
                    arr = np.array(vals, dtype=float)
                    lines.append(f"    {brain:15s}: mean={np.mean(arr):{fmt}}  "
                                 f"std={np.std(arr, ddof=1) if len(arr)>1 else 0:{fmt}}  n={len(arr)}")

    if HAS_SCIPY:
        lines.append(f"\n{'='*70}\nT-TESTS: Subsumption vs Coverage (dirt_collected)\n{'='*70}")
        for dt in durations:
            sub = [r["dirt_collected"] for r in rows
                   if r["brain_type"] == "Subsumption" and r["duration_type"] == dt]
            cov = [r["dirt_collected"] for r in rows
                   if r["brain_type"] == "Coverage" and r["duration_type"] == dt]
            if len(sub) >= 2 and len(cov) >= 2:
                t, p = scipy_stats.ttest_ind(sub, cov)
                sig = "*" if p < 0.05 else ""
                lines.append(f"  [{dt}] Subsumption vs Coverage: t={t:+.3f} p={p:.4f} {sig}")

    p = Path(out_dir) / "rq5_stats.txt"
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(p)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="experiments/results/rq5_coverage.csv")
    parser.add_argument("--timeline-input",
                        default="experiments/results/rq5_coverage_timeline.csv")
    parser.add_argument("--output-dir", default="docs/rq5-figures")
    args = parser.parse_args()

    Path(args.output_dir).mkdir(parents=True, exist_ok=True)
    _apply_style()
    rows = read_csv(args.input)
    generated = []

    for fn in (chart_coverage_comparison, chart_coverage_safety):
        try:
            r = fn(rows, args.output_dir)
            if r: generated.append(r)
        except Exception as e:
            print(f"WARNING: {e}", file=sys.stderr)

    if Path(args.timeline_input).is_file():
        try:
            t_rows = read_timeline_csv(args.timeline_input)
            r = chart_coverage_timeline(t_rows, args.output_dir)
            if r: generated.append(r)
        except Exception as e:
            print(f"WARNING: {e}", file=sys.stderr)

    try:
        generated.append(generate_stats(rows, args.output_dir))
    except Exception as e:
        print(f"WARNING: {e}", file=sys.stderr)

    print(f"Generated {len(generated)} outputs:")
    for p in generated:
        print(f"  {p}")


if __name__ == "__main__":
    main()
