#!/usr/bin/env python3
"""RQ4 Analysis: Reward function comparison charts and statistics."""
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

REWARD_ORDER = ["subsumption_baseline", "baseline", "heavy_safety",
                "dense_progress", "energy_aware", "sparse"]
REWARD_COLORS = {
    "subsumption_baseline": "#4C72B0",
    "baseline": "#55A868",
    "heavy_safety": "#C44E52",
    "dense_progress": "#8172B3",
    "energy_aware": "#DD8452",
    "sparse": "#937860",
}
REWARD_LABELS = {
    "subsumption_baseline": "Subsumption\n(baseline)",
    "baseline": "QL: Baseline",
    "heavy_safety": "QL: Heavy\nSafety",
    "dense_progress": "QL: Dense\nProgress",
    "energy_aware": "QL: Energy\nAware",
    "sparse": "QL: Sparse",
}


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


def read_eval_csv(path):
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            for k in ("seed", "frames", "dirt_collected", "cat_freeze_count", "battery_depletions"):
                if k in row:
                    try: row[k] = int(row[k])
                    except: row[k] = 0
            if "collection_rate" in row:
                try: row["collection_rate"] = float(row["collection_rate"])
                except: row["collection_rate"] = 0.0
            rows.append(row)
    return rows


def read_training_csv(path):
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try: row["episode"] = int(row["episode"])
            except: row["episode"] = 0
            try: row["total_reward"] = float(row["total_reward"])
            except: row["total_reward"] = 0.0
            try: row["dirt_collected"] = int(row["dirt_collected"])
            except: row["dirt_collected"] = 0
            rows.append(row)
    return rows


def chart_reward_comparison(rows, out_dir):
    groups = defaultdict(list)
    for r in rows:
        groups[r["reward_type"]].append(r["dirt_collected"])

    ordered = [rt for rt in REWARD_ORDER if rt in groups]
    means = [np.mean(groups[rt]) for rt in ordered]
    stds = [np.std(groups[rt], ddof=1) if len(groups[rt]) > 1 else 0 for rt in ordered]
    colors = [REWARD_COLORS.get(rt, "#999") for rt in ordered]
    labels = [REWARD_LABELS.get(rt, rt) for rt in ordered]

    fig, ax = plt.subplots(figsize=(12, 6))
    x = np.arange(len(ordered))
    ax.bar(x, means, yerr=stds, capsize=6, color=colors, edgecolor="white", width=0.6)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=10)
    _style_ax(ax, "Cleaning Performance by Reward Function", "Mean Dirt Collected")
    p = Path(out_dir) / "bar_reward_comparison.png"
    _savefig(fig, p)
    return str(p)


def chart_reward_training(training_rows, out_dir):
    """Overlay training curves for all reward variants."""
    data = defaultdict(lambda: {"episodes": [], "rewards": []})
    for r in training_rows:
        rt = r["reward_type"]
        data[rt]["episodes"].append(r["episode"])
        data[rt]["rewards"].append(r["total_reward"])

    fig, ax = plt.subplots(figsize=(10, 6))
    for rt in REWARD_ORDER:
        if rt not in data or rt == "subsumption_baseline":
            continue
        eps = np.array(data[rt]["episodes"], dtype=float)
        rews = np.array(data[rt]["rewards"], dtype=float)
        # Sort by episode
        order = np.argsort(eps)
        eps, rews = eps[order], rews[order]
        # Moving average
        if len(rews) >= 20:
            kernel = np.ones(20) / 20
            smoothed = np.convolve(rews, kernel, mode="valid")
            plot_eps = eps[:len(smoothed)]
        else:
            smoothed = rews
            plot_eps = eps
        c = REWARD_COLORS.get(rt, "#999")
        ax.plot(plot_eps, smoothed, color=c, linewidth=2,
                label=REWARD_LABELS.get(rt, rt).replace("\n", " "))

    ax.legend(fontsize=10)
    _style_ax(ax, "Training Curves by Reward Function (Smoothed)",
              "Total Reward (MA-20)", "Episode")
    p = Path(out_dir) / "line_reward_training.png"
    _savefig(fig, p)
    return str(p)


def chart_reward_safety(rows, out_dir):
    groups_f = defaultdict(list)
    groups_b = defaultdict(list)
    for r in rows:
        groups_f[r["reward_type"]].append(r["cat_freeze_count"])
        groups_b[r["reward_type"]].append(r["battery_depletions"])

    ordered = [rt for rt in REWARD_ORDER if rt in groups_f]
    labels = [REWARD_LABELS.get(rt, rt) for rt in ordered]

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    for ax, groups, title, ylabel in [
        (axes[0], groups_f, "Cat Freezes by Reward Function", "Mean Cat Freeze Events"),
        (axes[1], groups_b, "Battery Depletions by Reward Function", "Mean Battery Depletions"),
    ]:
        means = [np.mean(groups[rt]) for rt in ordered]
        colors = [REWARD_COLORS.get(rt, "#999") for rt in ordered]
        x = np.arange(len(ordered))
        ax.bar(x, means, color=colors, edgecolor="white", width=0.6)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=9)
        _style_ax(ax, title, ylabel)

    p = Path(out_dir) / "bar_reward_safety.png"
    _savefig(fig, p)
    return str(p)


def chart_reward_stability(rows, out_dir):
    groups = defaultdict(list)
    for r in rows:
        groups[r["reward_type"]].append(r["dirt_collected"])

    ordered = [rt for rt in REWARD_ORDER if rt in groups]
    vals = [groups[rt] for rt in ordered]
    labels = [REWARD_LABELS.get(rt, rt) for rt in ordered]
    colors = [REWARD_COLORS.get(rt, "#999") for rt in ordered]

    fig, ax = plt.subplots(figsize=(12, 6))
    bp = ax.boxplot(vals, patch_artist=True, tick_labels=labels, widths=0.5)
    for patch, c in zip(bp["boxes"], colors):
        patch.set_facecolor(c)
        patch.set_alpha(0.75)
    _style_ax(ax, "Performance Stability by Reward Function",
              "Dirt Collected")
    p = Path(out_dir) / "box_reward_stability.png"
    _savefig(fig, p)
    return str(p)


def generate_stats(rows, out_dir):
    lines = ["=" * 70, "RQ4: REWARD FUNCTION COMPARISON - STATISTICS", "=" * 70]
    reward_types = [rt for rt in REWARD_ORDER if any(r["reward_type"] == rt for r in rows)]

    for metric in ("dirt_collected", "cat_freeze_count", "battery_depletions"):
        lines.append(f"\n--- {metric} ---")
        for rt in reward_types:
            vals = [r[metric] for r in rows if r["reward_type"] == rt]
            if vals:
                arr = np.array(vals, dtype=float)
                lines.append(f"  {rt:20s}: mean={np.mean(arr):.2f}  "
                             f"std={np.std(arr, ddof=1) if len(arr)>1 else 0:.2f}  n={len(arr)}")

    if HAS_SCIPY and len(reward_types) >= 2:
        lines.append(f"\n{'='*70}\nT-TESTS: baseline vs each variant (dirt_collected)\n{'='*70}")
        baseline_vals = [r["dirt_collected"] for r in rows if r["reward_type"] == "baseline"]
        for rt in reward_types:
            if rt == "baseline":
                continue
            other = [r["dirt_collected"] for r in rows if r["reward_type"] == rt]
            if len(baseline_vals) >= 2 and len(other) >= 2:
                t, p = scipy_stats.ttest_ind(baseline_vals, other)
                sig = "*" if p < 0.05 else ""
                lines.append(f"  baseline vs {rt}: t={t:+.3f} p={p:.4f} {sig}")

    p = Path(out_dir) / "rq4_stats.txt"
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(p)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="experiments/results/rq4_rewards.csv")
    parser.add_argument("--training-input", default="experiments/results/rq4_training_all.csv")
    parser.add_argument("--output-dir", default="docs/rq4-figures")
    args = parser.parse_args()

    Path(args.output_dir).mkdir(parents=True, exist_ok=True)
    _apply_style()

    rows = read_eval_csv(args.input)
    generated = []

    for fn in (chart_reward_comparison, chart_reward_safety, chart_reward_stability):
        try:
            r = fn(rows, args.output_dir)
            if r: generated.append(r)
        except Exception as e:
            print(f"WARNING: {e}", file=sys.stderr)

    # Training curves
    if Path(args.training_input).is_file():
        try:
            t_rows = read_training_csv(args.training_input)
            r = chart_reward_training(t_rows, args.output_dir)
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
