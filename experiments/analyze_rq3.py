#!/usr/bin/env python3
"""RQ3 Analysis: Sensor noise robustness charts and statistics."""
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
            for k in ("seed", "frames", "dirt_collected", "cat_freeze_count", "battery_depletions"):
                if k in row:
                    try: row[k] = int(row[k])
                    except: row[k] = 0
            for k in ("collection_rate", "noise_sigma"):
                if k in row:
                    try: row[k] = float(row[k])
                    except: row[k] = 0.0
            rows.append(row)
    return rows


def chart_noise_degradation(rows, out_dir):
    data = defaultdict(lambda: defaultdict(list))
    for r in rows:
        data[r["brain_type"]][r["noise_sigma"]].append(r["dirt_collected"])

    fig, ax = plt.subplots(figsize=(10, 6))
    for brain in BRAIN_ORDER:
        if brain not in data:
            continue
        sigmas = sorted(data[brain].keys())
        means = [np.mean(data[brain][s]) for s in sigmas]
        stds = [np.std(data[brain][s], ddof=1) if len(data[brain][s]) > 1 else 0 for s in sigmas]
        c = COLORS.get(brain, "#999")
        ax.plot(sigmas, means, "o-", color=c, linewidth=2, label=brain)
        ax.fill_between(sigmas, np.array(means) - np.array(stds),
                        np.array(means) + np.array(stds), color=c, alpha=0.2)
    ax.legend(fontsize=11)
    _style_ax(ax, "Cleaning Performance Under Sensor Noise",
              "Mean Dirt Collected", "Noise Level (sigma)")
    p = Path(out_dir) / "line_noise_degradation.png"
    _savefig(fig, p)
    return str(p)


def chart_noise_safety(rows, out_dir):
    data = defaultdict(lambda: defaultdict(list))
    for r in rows:
        data[r["brain_type"]][r["noise_sigma"]].append(r["cat_freeze_count"])

    fig, ax = plt.subplots(figsize=(10, 6))
    for brain in BRAIN_ORDER:
        if brain not in data:
            continue
        sigmas = sorted(data[brain].keys())
        means = [np.mean(data[brain][s]) for s in sigmas]
        stds = [np.std(data[brain][s], ddof=1) if len(data[brain][s]) > 1 else 0
                for s in sigmas]
        c = COLORS.get(brain, "#999")
        ax.plot(sigmas, means, "o-", color=c, linewidth=2, label=brain)
        ax.fill_between(sigmas, np.array(means) - np.array(stds),
                        np.array(means) + np.array(stds), color=c, alpha=0.2)
    ax.legend(fontsize=11)
    _style_ax(ax, "Cat Freeze Events Under Sensor Noise",
              "Mean Cat Freeze Events", "Noise Level (sigma)")
    p = Path(out_dir) / "line_noise_safety.png"
    _savefig(fig, p)
    return str(p)


def chart_noise_relative(rows, out_dir):
    """Bar chart: % of baseline performance retained at each noise level."""
    data = defaultdict(lambda: defaultdict(list))
    for r in rows:
        data[r["brain_type"]][r["noise_sigma"]].append(r["dirt_collected"])

    fig, ax = plt.subplots(figsize=(10, 6))
    for brain in BRAIN_ORDER:
        if brain not in data or 0.0 not in data[brain]:
            continue
        baseline = np.mean(data[brain][0.0])
        if baseline == 0:
            continue
        sigmas = sorted(data[brain].keys())
        pcts = [np.mean(data[brain][s]) / baseline * 100 for s in sigmas]
        c = COLORS.get(brain, "#999")
        ax.plot(sigmas, pcts, "o-", color=c, linewidth=2, label=brain)
    ax.axhline(y=100, linestyle="--", color="gray", alpha=0.5)
    ax.legend(fontsize=11)
    _style_ax(ax, "Performance Retention Under Noise (% of Baseline)",
              "Performance Retained (%)", "Noise Level (sigma)")
    p = Path(out_dir) / "bar_noise_relative.png"
    _savefig(fig, p)
    return str(p)


def generate_stats(rows, out_dir):
    lines = ["=" * 70, "RQ3: SENSOR NOISE ROBUSTNESS - STATISTICS", "=" * 70]
    brains = [b for b in BRAIN_ORDER if any(r["brain_type"] == b for r in rows)]
    sigmas = sorted(set(r["noise_sigma"] for r in rows))

    for metric in ("dirt_collected", "cat_freeze_count", "battery_depletions"):
        lines.append(f"\n--- {metric} ---")
        for brain in brains:
            lines.append(f"  {brain}:")
            for s in sigmas:
                vals = [r[metric] for r in rows
                        if r["brain_type"] == brain and r["noise_sigma"] == s]
                if vals:
                    arr = np.array(vals, dtype=float)
                    lines.append(f"    sigma={s:.1f}: mean={np.mean(arr):.2f}  "
                                 f"std={np.std(arr, ddof=1) if len(arr)>1 else 0:.2f}  n={len(arr)}")

    if HAS_SCIPY:
        for metric_label, metric_col in [("dirt_collected", "dirt_collected"),
                                          ("cat_freeze_count", "cat_freeze_count")]:
            lines.append(f"\n{'='*70}\nT-TESTS: sigma=0 vs each noise level ({metric_label})\n{'='*70}")
            for brain in brains:
                lines.append(f"\n  {brain}:")
                baseline = [r[metric_col] for r in rows
                            if r["brain_type"] == brain and r["noise_sigma"] == 0.0]
                for s in sigmas:
                    if s == 0.0:
                        continue
                    noisy = [r[metric_col] for r in rows
                             if r["brain_type"] == brain and r["noise_sigma"] == s]
                    if len(baseline) >= 2 and len(noisy) >= 2:
                        t, p = scipy_stats.ttest_ind(baseline, noisy)
                        sig = "*" if p < 0.05 else ""
                        lines.append(f"    0.0 vs {s:.1f}: t={t:+.3f} p={p:.4f} {sig}")

    p = Path(out_dir) / "rq3_stats.txt"
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(p)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="experiments/results/rq3_noise.csv")
    parser.add_argument("--output-dir", default="docs/rq3-figures")
    args = parser.parse_args()

    Path(args.output_dir).mkdir(parents=True, exist_ok=True)
    _apply_style()
    rows = read_csv(args.input)
    generated = []
    for fn in (chart_noise_degradation, chart_noise_safety, chart_noise_relative):
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
