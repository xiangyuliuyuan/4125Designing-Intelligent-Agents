#!/usr/bin/env python3
"""RQ2 Analysis: Robot count scaling charts and statistics."""
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

BRAIN_ORDER = ["Subsumption", "Potential Field", "Q-Learning"]
COLORS = {"Subsumption": "#4C72B0", "Potential Field": "#DD8452", "Q-Learning": "#55A868"}
_BRAIN_ALIASES = {
    "subsumption": "Subsumption", "potential_field": "Potential Field",
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
            for k in ("seed", "frames", "bot_count", "dirt_collected",
                       "cat_freeze_count", "battery_depletions"):
                if k in row:
                    try: row[k] = int(row[k])
                    except: row[k] = 0
            for k in ("collection_rate", "dirt_per_bot"):
                if k in row:
                    try: row[k] = float(row[k])
                    except: row[k] = 0.0
            rows.append(row)
    return rows


def chart_scaling_total(rows, out_dir):
    data = defaultdict(lambda: defaultdict(list))
    for r in rows:
        data[r["brain_type"]][r["bot_count"]].append(r["dirt_collected"])

    fig, ax = plt.subplots(figsize=(10, 6))
    for brain in BRAIN_ORDER:
        if brain not in data:
            continue
        bots = sorted(data[brain].keys())
        means = [np.mean(data[brain][b]) for b in bots]
        stds = [np.std(data[brain][b], ddof=1) if len(data[brain][b]) > 1 else 0 for b in bots]
        c = COLORS.get(brain, "#999")
        ax.plot(bots, means, "o-", color=c, linewidth=2, label=brain)
        ax.fill_between(bots, np.array(means) - np.array(stds),
                        np.array(means) + np.array(stds), color=c, alpha=0.2)
    ax.legend(fontsize=11)
    _style_ax(ax, "Total Cleaning Performance vs Robot Count",
              "Mean Dirt Collected", "Number of Robots")
    p = Path(out_dir) / "line_scaling_total.png"
    _savefig(fig, p)
    return str(p)


def chart_scaling_per_bot(rows, out_dir):
    data = defaultdict(lambda: defaultdict(list))
    for r in rows:
        data[r["brain_type"]][r["bot_count"]].append(r["dirt_per_bot"])

    fig, ax = plt.subplots(figsize=(10, 6))
    for brain in BRAIN_ORDER:
        if brain not in data:
            continue
        bots = sorted(data[brain].keys())
        means = [np.mean(data[brain][b]) for b in bots]
        stds = [np.std(data[brain][b], ddof=1) if len(data[brain][b]) > 1 else 0 for b in bots]
        c = COLORS.get(brain, "#999")
        ax.plot(bots, means, "o-", color=c, linewidth=2, label=brain)
        ax.fill_between(bots, np.array(means) - np.array(stds),
                        np.array(means) + np.array(stds), color=c, alpha=0.2)
    ax.legend(fontsize=11)
    _style_ax(ax, "Per-Robot Efficiency vs Robot Count (Diminishing Returns)",
              "Mean Dirt per Robot", "Number of Robots")
    p = Path(out_dir) / "line_scaling_per_bot.png"
    _savefig(fig, p)
    return str(p)


def chart_scaling_safety(rows, out_dir):
    data_freeze = defaultdict(lambda: defaultdict(list))
    data_batt = defaultdict(lambda: defaultdict(list))
    for r in rows:
        data_freeze[r["brain_type"]][r["bot_count"]].append(r["cat_freeze_count"])
        data_batt[r["brain_type"]][r["bot_count"]].append(r["battery_depletions"])

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    for ax, data, title, ylabel in [
        (axes[0], data_freeze, "Cat Freezes vs Robot Count", "Mean Cat Freeze Events"),
        (axes[1], data_batt, "Battery Depletions vs Robot Count", "Mean Battery Depletions"),
    ]:
        for brain in BRAIN_ORDER:
            if brain not in data:
                continue
            bots = sorted(data[brain].keys())
            means = [np.mean(data[brain][b]) for b in bots]
            c = COLORS.get(brain, "#999")
            ax.plot(bots, means, "o-", color=c, linewidth=2, label=brain)
        ax.legend(fontsize=10)
        _style_ax(ax, title, ylabel, "Number of Robots")

    p = Path(out_dir) / "bar_scaling_safety.png"
    _savefig(fig, p)
    return str(p)


def generate_stats(rows, out_dir):
    lines = ["=" * 70, "RQ2: ROBOT COUNT SCALING - STATISTICS", "=" * 70]
    brains = [b for b in BRAIN_ORDER if any(r["brain_type"] == b for r in rows)]
    bot_counts = sorted(set(r["bot_count"] for r in rows))

    for metric in ("dirt_collected", "dirt_per_bot", "cat_freeze_count", "battery_depletions"):
        lines.append(f"\n--- {metric} ---")
        for brain in brains:
            lines.append(f"  {brain}:")
            for bc in bot_counts:
                vals = [r[metric] for r in rows
                        if r["brain_type"] == brain and r["bot_count"] == bc]
                if vals:
                    arr = np.array(vals, dtype=float)
                    lines.append(f"    bots={bc:2d}: mean={np.mean(arr):.2f}  "
                                 f"std={np.std(arr, ddof=1) if len(arr)>1 else 0:.2f}  n={len(arr)}")

    if HAS_SCIPY:
        lines.append(f"\n{'='*70}\nPAIRWISE T-TESTS (dirt_collected, adjacent bot counts)\n{'='*70}")
        for brain in brains:
            lines.append(f"\n  {brain}:")
            for i in range(len(bot_counts) - 1):
                v1 = [r["dirt_collected"] for r in rows
                      if r["brain_type"] == brain and r["bot_count"] == bot_counts[i]]
                v2 = [r["dirt_collected"] for r in rows
                      if r["brain_type"] == brain and r["bot_count"] == bot_counts[i+1]]
                if len(v1) >= 2 and len(v2) >= 2:
                    t, p = scipy_stats.ttest_ind(v1, v2)
                    sig = "*" if p < 0.05 else ""
                    lines.append(f"    {bot_counts[i]} vs {bot_counts[i+1]}: "
                                 f"t={t:+.3f} p={p:.4f} {sig}")

    p = Path(out_dir) / "rq2_stats.txt"
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(p)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="experiments/results/rq2_scaling.csv")
    parser.add_argument("--output-dir", default="docs/rq2-figures")
    args = parser.parse_args()

    Path(args.output_dir).mkdir(parents=True, exist_ok=True)
    _apply_style()
    rows = read_csv(args.input)
    generated = []
    for fn in (chart_scaling_total, chart_scaling_per_bot, chart_scaling_safety):
        try:
            r = fn(rows, args.output_dir)
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
