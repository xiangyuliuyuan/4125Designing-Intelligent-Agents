"""Analyze experiment CSV results and generate publication-quality charts."""

import argparse
import csv
import json
import sys
import os
from pathlib import Path
from collections import defaultdict, Counter

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# ---------------------------------------------------------------------------
# Optional scientific-Python imports -- degrade gracefully if missing
# ---------------------------------------------------------------------------
try:
    import matplotlib
    matplotlib.use("Agg")  # non-interactive backend
    import matplotlib.pyplot as plt
    HAS_MPL = True
except ImportError:
    HAS_MPL = False

try:
    import numpy as np
    HAS_NP = True
except ImportError:
    HAS_NP = False

try:
    from scipy import stats as scipy_stats
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
BRAIN_ORDER = ["Subsumption", "Potential Field", "Q-Learning"]
COLORS = {"Subsumption": "#4C72B0", "Potential Field": "#DD8452", "Q-Learning": "#55A868"}

# Action names used in Q-table visualisation
ACTION_NAMES = ["FORWARD", "TURN_LEFT", "TURN_RIGHT", "GRAB", "GO_HOME"]

# Mapping from raw CSV brain_type values to canonical Title Case labels
_BRAIN_ALIASES = {
    "subsumption": "Subsumption",
    "potential_field": "Potential Field",
    "potentialfield": "Potential Field",
    "apf": "Potential Field",
    "q_learning": "Q-Learning",
    "qlearning": "Q-Learning",
    "ql": "Q-Learning",
}


def _canonicalise_brain(raw: str) -> str:
    """Return the canonical brain-type label for *raw*."""
    key = raw.strip().lower().replace("-", "_").replace(" ", "_")
    return _BRAIN_ALIASES.get(key, raw.strip())


# ---------------------------------------------------------------------------
# Style helpers
# ---------------------------------------------------------------------------
def _apply_style():
    """Apply a clean chart style, falling back gracefully."""
    for style in ("seaborn-v0_8-whitegrid", "seaborn-whitegrid", "ggplot"):
        try:
            plt.style.use(style)
            return
        except OSError:
            continue
    # If none available, just continue with defaults


def _style_ax(ax, title, ylabel, xlabel=None):
    """Apply common axis styling."""
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


# ---------------------------------------------------------------------------
# CSV readers
# ---------------------------------------------------------------------------
def read_comparison_csv(path: str):
    """Return list of dicts from comparison.csv."""
    rows = []
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            row["brain_type"] = _canonicalise_brain(row["brain_type"])
            for key in ("seed", "frames", "dirt_collected", "cat_freeze_count", "battery_depletions"):
                if key in row:
                    try:
                        row[key] = int(row[key])
                    except (ValueError, TypeError):
                        row[key] = 0
            if "collection_rate" in row:
                try:
                    row["collection_rate"] = float(row["collection_rate"])
                except (ValueError, TypeError):
                    row["collection_rate"] = 0.0
            rows.append(row)
    return rows


def read_training_csv(path: str):
    """Return list of dicts from training_curve.csv."""
    rows = []
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            for key in ("episode", "dirt_collected"):
                if key in row:
                    try:
                        row[key] = int(row[key])
                    except (ValueError, TypeError):
                        row[key] = 0
            for key in ("total_reward", "epsilon"):
                if key in row:
                    try:
                        row[key] = float(row[key])
                    except (ValueError, TypeError):
                        row[key] = 0.0
            rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# Aggregation helpers
# ---------------------------------------------------------------------------
def _group_by_brain(rows, metric):
    """Return {brain_type: [values]} for *metric*."""
    groups = defaultdict(list)
    for r in rows:
        if metric in r:
            groups[r["brain_type"]].append(r[metric])
    return groups


def _ordered_groups(groups):
    """Return (labels, value_lists) in BRAIN_ORDER, skipping missing."""
    labels, vals = [], []
    for b in BRAIN_ORDER:
        if b in groups:
            labels.append(b)
            vals.append(groups[b])
    # Append any brains not in the predefined order
    for b in sorted(groups):
        if b not in labels:
            labels.append(b)
            vals.append(groups[b])
    return labels, vals


# ---------------------------------------------------------------------------
# Chart: bar_dirt_collected.png
# ---------------------------------------------------------------------------
def chart_bar_dirt_collected(rows, output_dir):
    groups = _group_by_brain(rows, "dirt_collected")
    labels, vals = _ordered_groups(groups)
    if not labels:
        return None
    means = [np.mean(v) for v in vals]
    stds = [np.std(v, ddof=1) if len(v) > 1 else 0.0 for v in vals]
    colors = [COLORS.get(l, "#999999") for l in labels]

    fig, ax = plt.subplots(figsize=(10, 6))
    x = np.arange(len(labels))
    ax.bar(x, means, yerr=stds, capsize=6, color=colors, edgecolor="white", width=0.55)
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    _style_ax(ax, "Cleaning Performance Comparison", "Mean Dirt Collected")

    path = Path(output_dir) / "bar_dirt_collected.png"
    _savefig(fig, path)
    return str(path)


# ---------------------------------------------------------------------------
# Chart: box_collection_rate.png
# ---------------------------------------------------------------------------
def chart_box_collection_rate(rows, output_dir):
    groups = _group_by_brain(rows, "collection_rate")
    labels, vals = _ordered_groups(groups)
    if not labels:
        return None
    colors = [COLORS.get(l, "#999999") for l in labels]

    fig, ax = plt.subplots(figsize=(10, 6))
    bp = ax.boxplot(vals, patch_artist=True, labels=labels, widths=0.5)
    for patch, c in zip(bp["boxes"], colors):
        patch.set_facecolor(c)
        patch.set_alpha(0.75)
    _style_ax(ax, "Distribution of Collection Rates", "Collection Rate (dirt/frame)")

    path = Path(output_dir) / "box_collection_rate.png"
    _savefig(fig, path)
    return str(path)


# ---------------------------------------------------------------------------
# Chart: bar_cat_freezes.png
# ---------------------------------------------------------------------------
def chart_bar_cat_freezes(rows, output_dir):
    groups = _group_by_brain(rows, "cat_freeze_count")
    labels, vals = _ordered_groups(groups)
    if not labels:
        return None
    means = [np.mean(v) for v in vals]
    stds = [np.std(v, ddof=1) if len(v) > 1 else 0.0 for v in vals]
    colors = [COLORS.get(l, "#999999") for l in labels]

    fig, ax = plt.subplots(figsize=(10, 6))
    x = np.arange(len(labels))
    ax.bar(x, means, yerr=stds, capsize=6, color=colors, edgecolor="white", width=0.55)
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    _style_ax(ax, "Cat Encounter Safety Comparison", "Mean Cat Freeze Events")

    path = Path(output_dir) / "bar_cat_freezes.png"
    _savefig(fig, path)
    return str(path)


# ---------------------------------------------------------------------------
# Chart: bar_battery.png
# ---------------------------------------------------------------------------
def chart_bar_battery(rows, output_dir):
    groups = _group_by_brain(rows, "battery_depletions")
    labels, vals = _ordered_groups(groups)
    if not labels:
        return None
    means = [np.mean(v) for v in vals]
    stds = [np.std(v, ddof=1) if len(v) > 1 else 0.0 for v in vals]
    colors = [COLORS.get(l, "#999999") for l in labels]

    fig, ax = plt.subplots(figsize=(10, 6))
    x = np.arange(len(labels))
    ax.bar(x, means, yerr=stds, capsize=6, color=colors, edgecolor="white", width=0.55)
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    _style_ax(ax, "Energy Management Comparison", "Mean Battery Depletions")

    path = Path(output_dir) / "bar_battery.png"
    _savefig(fig, path)
    return str(path)


# ---------------------------------------------------------------------------
# Chart: radar_comparison.png
# ---------------------------------------------------------------------------
def chart_radar_comparison(rows, output_dir):
    """Multi-metric radar / spider chart with values normalised to [0, 1]."""
    metrics = {
        "cleaning_efficiency": "dirt_collected",
        "safety": "cat_freeze_count",
        "energy_management": "battery_depletions",
    }
    groups_raw = {}
    for label, col in metrics.items():
        groups_raw[label] = _group_by_brain(rows, col)

    # Determine which brain types are present in all metrics
    brain_sets = [set(g.keys()) for g in groups_raw.values()]
    common_brains = brain_sets[0]
    for s in brain_sets[1:]:
        common_brains &= s
    ordered = [b for b in BRAIN_ORDER if b in common_brains]
    if len(ordered) < 2:
        return None

    metric_names = list(metrics.keys())
    means = {}  # {brain: [mean_per_metric]}
    for brain in ordered:
        means[brain] = []
        for m_label, col in metrics.items():
            vals = groups_raw[m_label][brain]
            means[brain].append(np.mean(vals))

    # Normalise each metric to [0, 1].  For safety and energy_management,
    # *lower* is better so we invert after normalising.
    n_metrics = len(metric_names)
    all_vals_per_metric = []
    for i in range(n_metrics):
        all_vals_per_metric.append([means[b][i] for b in ordered])

    normed = {b: [] for b in ordered}
    invert = {"safety", "energy_management"}  # lower is better
    for i, m_label in enumerate(metric_names):
        col_vals = [means[b][i] for b in ordered]
        lo, hi = min(col_vals), max(col_vals)
        span = hi - lo if hi != lo else 1.0
        for brain in ordered:
            v = (means[brain][i] - lo) / span
            if m_label in invert:
                v = 1.0 - v
            normed[brain].append(v)

    angles = np.linspace(0, 2 * np.pi, n_metrics, endpoint=False).tolist()
    angles += angles[:1]  # close polygon

    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw={"polar": True})
    for brain in ordered:
        values = normed[brain] + normed[brain][:1]
        color = COLORS.get(brain, "#999999")
        ax.plot(angles, values, "o-", linewidth=2, label=brain, color=color)
        ax.fill(angles, values, alpha=0.15, color=color)

    display_labels = [m.replace("_", " ").title() for m in metric_names]
    ax.set_thetagrids(np.degrees(angles[:-1]), display_labels, fontsize=12)
    ax.set_ylim(0, 1.05)
    ax.set_title("Multi-Metric Comparison (normalised)", fontsize=14, pad=20)
    ax.legend(loc="upper right", bbox_to_anchor=(1.25, 1.1), fontsize=11)

    path = Path(output_dir) / "radar_comparison.png"
    _savefig(fig, path)
    return str(path)


# ---------------------------------------------------------------------------
# Stats summary (text)
# ---------------------------------------------------------------------------
def generate_stats_summary(rows, output_dir):
    """Write descriptive stats and optional t-test results to stats_summary.txt."""
    metric_cols = ["dirt_collected", "collection_rate", "cat_freeze_count", "battery_depletions"]
    groups_all = {}
    for col in metric_cols:
        groups_all[col] = _group_by_brain(rows, col)

    # Determine ordered brains present
    all_brains = set()
    for g in groups_all.values():
        all_brains |= set(g.keys())
    ordered = [b for b in BRAIN_ORDER if b in all_brains]
    for b in sorted(all_brains):
        if b not in ordered:
            ordered.append(b)

    lines = []
    lines.append("=" * 70)
    lines.append("EXPERIMENT RESULTS - DESCRIPTIVE STATISTICS")
    lines.append("=" * 70)

    for col in metric_cols:
        lines.append("")
        lines.append(f"--- {col} ---")
        for brain in ordered:
            vals = groups_all[col].get(brain, [])
            if not vals:
                continue
            arr = np.array(vals, dtype=float)
            lines.append(
                f"  {brain:20s}  mean={np.mean(arr):8.3f}  std={np.std(arr, ddof=1) if len(arr) > 1 else 0:8.3f}"
                f"  min={np.min(arr):8.3f}  max={np.max(arr):8.3f}  n={len(arr)}"
            )

    # Pairwise t-tests
    if HAS_SCIPY and len(ordered) >= 2:
        lines.append("")
        lines.append("=" * 70)
        lines.append("PAIRWISE T-TESTS (independent, two-sided)")
        lines.append("=" * 70)
        pairs = []
        for i in range(len(ordered)):
            for j in range(i + 1, len(ordered)):
                pairs.append((ordered[i], ordered[j]))
        for col in metric_cols:
            lines.append("")
            lines.append(f"--- {col} ---")
            for b1, b2 in pairs:
                v1 = groups_all[col].get(b1, [])
                v2 = groups_all[col].get(b2, [])
                if len(v1) < 2 or len(v2) < 2:
                    lines.append(f"  {b1} vs {b2}: insufficient data (n1={len(v1)}, n2={len(v2)})")
                    continue
                t_stat, p_val = scipy_stats.ttest_ind(v1, v2)
                sig = "*" if p_val < 0.05 else ""
                lines.append(f"  {b1} vs {b2}: t={t_stat:+.4f}  p={p_val:.4f} {sig}")
    elif not HAS_SCIPY:
        lines.append("")
        lines.append("(scipy not available -- t-tests skipped)")

    text = "\n".join(lines) + "\n"
    path = Path(output_dir) / "stats_summary.txt"
    path.write_text(text, encoding="utf-8")
    return str(path)


# ---------------------------------------------------------------------------
# Training curve charts
# ---------------------------------------------------------------------------
def _moving_average(values, window=20):
    """Simple centred moving average; pads edges with original values."""
    if len(values) < window:
        return values
    kernel = np.ones(window) / window
    smoothed = np.convolve(values, kernel, mode="valid")
    pad_left = (len(values) - len(smoothed)) // 2
    pad_right = len(values) - len(smoothed) - pad_left
    return np.concatenate([values[:pad_left], smoothed, values[len(values) - pad_right:]])


def chart_training_reward(rows, output_dir):
    episodes = np.array([r["episode"] for r in rows], dtype=float)
    rewards = np.array([r["total_reward"] for r in rows], dtype=float)
    if len(episodes) == 0:
        return None

    smoothed = _moving_average(rewards, window=20)

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(episodes, rewards, alpha=0.3, color="#4C72B0", label="Raw")
    ax.plot(episodes, smoothed, color="#4C72B0", linewidth=2, label="Moving Avg (w=20)")
    ax.legend(fontsize=11)
    _style_ax(ax, "Q-Learning Training Curve (Reward)", "Total Reward", "Episode")

    path = Path(output_dir) / "training_curve_reward.png"
    _savefig(fig, path)
    return str(path)


def chart_training_dirt(rows, output_dir):
    episodes = np.array([r["episode"] for r in rows], dtype=float)
    dirt = np.array([r["dirt_collected"] for r in rows], dtype=float)
    if len(episodes) == 0:
        return None

    smoothed = _moving_average(dirt, window=20)

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(episodes, dirt, alpha=0.3, color="#55A868", label="Raw")
    ax.plot(episodes, smoothed, color="#55A868", linewidth=2, label="Moving Avg (w=20)")
    ax.legend(fontsize=11)
    _style_ax(ax, "Q-Learning Training Curve (Dirt Collected)", "Dirt Collected", "Episode")

    path = Path(output_dir) / "training_curve_dirt.png"
    _savefig(fig, path)
    return str(path)


# ---------------------------------------------------------------------------
# CSV readers: cat_gradient & training_duration
# ---------------------------------------------------------------------------
def read_cat_gradient_csv(path: str):
    """Return list of dicts from cat_gradient.csv."""
    rows = []
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            row["brain_type"] = _canonicalise_brain(row["brain_type"])
            for key in ("seed", "frames", "dirt_collected", "cat_freeze_count",
                        "battery_depletions", "cat_count"):
                if key in row:
                    try:
                        row[key] = int(row[key])
                    except (ValueError, TypeError):
                        row[key] = 0
            if "collection_rate" in row:
                try:
                    row["collection_rate"] = float(row["collection_rate"])
                except (ValueError, TypeError):
                    row["collection_rate"] = 0.0
            rows.append(row)
    return rows


def read_training_duration_csv(path: str):
    """Return list of dicts from training_duration.csv."""
    rows = []
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            row["brain_type"] = _canonicalise_brain(row["brain_type"])
            for key in ("seed", "frames", "dirt_collected", "cat_freeze_count",
                        "battery_depletions", "training_episodes"):
                if key in row:
                    try:
                        row[key] = int(row[key])
                    except (ValueError, TypeError):
                        row[key] = 0
            if "collection_rate" in row:
                try:
                    row["collection_rate"] = float(row["collection_rate"])
                except (ValueError, TypeError):
                    row["collection_rate"] = 0.0
            rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# Chart: line_cat_gradient.png
# ---------------------------------------------------------------------------
def chart_line_cat_gradient(rows, output_dir):
    """Line chart with error bands: dirt collected vs cat count per brain type."""
    # Group by (brain_type, cat_count)
    data = defaultdict(lambda: defaultdict(list))
    for r in rows:
        data[r["brain_type"]][r["cat_count"]].append(r["dirt_collected"])

    if not data:
        return None

    fig, ax = plt.subplots(figsize=(10, 6))
    for brain in BRAIN_ORDER:
        if brain not in data:
            continue
        cat_counts = sorted(data[brain].keys())
        means = [np.mean(data[brain][c]) for c in cat_counts]
        stds = [np.std(data[brain][c], ddof=1) if len(data[brain][c]) > 1 else 0.0
                for c in cat_counts]
        color = COLORS.get(brain, "#999999")
        means_arr = np.array(means)
        stds_arr = np.array(stds)
        ax.plot(cat_counts, means, "o-", color=color, linewidth=2, label=brain)
        ax.fill_between(cat_counts, means_arr - stds_arr, means_arr + stds_arr,
                        color=color, alpha=0.2)

    ax.legend(fontsize=11)
    _style_ax(ax, "Impact of Cat Count on Cleaning Performance",
              "Mean Dirt Collected", "Cat Count")

    path = Path(output_dir) / "line_cat_gradient.png"
    _savefig(fig, path)
    return str(path)


# ---------------------------------------------------------------------------
# Chart: line_cat_gradient_rate.png
# ---------------------------------------------------------------------------
def chart_line_cat_gradient_rate(rows, output_dir):
    """Line chart with error bands: collection rate vs cat count per brain type."""
    data = defaultdict(lambda: defaultdict(list))
    for r in rows:
        data[r["brain_type"]][r["cat_count"]].append(r["collection_rate"])

    if not data:
        return None

    fig, ax = plt.subplots(figsize=(10, 6))
    for brain in BRAIN_ORDER:
        if brain not in data:
            continue
        cat_counts = sorted(data[brain].keys())
        means = [np.mean(data[brain][c]) for c in cat_counts]
        stds = [np.std(data[brain][c], ddof=1) if len(data[brain][c]) > 1 else 0.0
                for c in cat_counts]
        color = COLORS.get(brain, "#999999")
        means_arr = np.array(means)
        stds_arr = np.array(stds)
        ax.plot(cat_counts, means, "o-", color=color, linewidth=2, label=brain)
        ax.fill_between(cat_counts, means_arr - stds_arr, means_arr + stds_arr,
                        color=color, alpha=0.2)

    ax.legend(fontsize=11)
    _style_ax(ax, "Impact of Cat Count on Collection Rate",
              "Collection Rate (dirt/frame)", "Cat Count")

    path = Path(output_dir) / "line_cat_gradient_rate.png"
    _savefig(fig, path)
    return str(path)


# ---------------------------------------------------------------------------
# Chart: line_training_duration.png
# ---------------------------------------------------------------------------
def chart_line_training_duration(rows, output_dir, comparison_rows=None):
    """Line chart: Q-Learning dirt collected vs training episodes, with baselines."""
    # Filter Q-Learning rows only
    ql_data = defaultdict(list)
    for r in rows:
        if r["brain_type"] == "Q-Learning":
            ql_data[r["training_episodes"]].append(r["dirt_collected"])

    if not ql_data:
        return None

    episodes = sorted(ql_data.keys())
    means = [np.mean(ql_data[e]) for e in episodes]
    stds = [np.std(ql_data[e], ddof=1) if len(ql_data[e]) > 1 else 0.0
            for e in episodes]

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.errorbar(episodes, means, yerr=stds, fmt="o-", color=COLORS["Q-Learning"],
                linewidth=2, capsize=6, label="Q-Learning")

    # Add baseline dashed lines from comparison.csv if available
    if comparison_rows:
        baselines = _group_by_brain(comparison_rows, "dirt_collected")
        for brain, style in [("Subsumption", "--"), ("Potential Field", ":")]:
            if brain in baselines and baselines[brain]:
                baseline_mean = np.mean(baselines[brain])
                ax.axhline(y=baseline_mean, linestyle=style,
                           color=COLORS.get(brain, "#999999"), linewidth=1.5,
                           label=f"{brain} baseline ({baseline_mean:.1f})")

    ax.legend(fontsize=11)
    _style_ax(ax, "Effect of Training Duration on Q-Learning Performance",
              "Mean Dirt Collected", "Training Episodes")

    path = Path(output_dir) / "line_training_duration.png"
    _savefig(fig, path)
    return str(path)


# ---------------------------------------------------------------------------
# Q-table parsing helpers
# ---------------------------------------------------------------------------
def _parse_qtable(path: str):
    """Parse a Q-table JSON file into {(state_tuple, action_index): q_value}.

    Keys in the JSON have the form:
        "('left', 'none', 'high', 'low', 'low', 'low'), 0"
    """
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)

    parsed = {}
    for key_str, value in raw.items():
        # Split on the last comma before the action integer
        # Format: "(<state tuple>), <action>"
        last_paren = key_str.rfind(")")
        if last_paren == -1:
            continue
        state_part = key_str[:last_paren + 1].strip()
        action_part = key_str[last_paren + 1:].strip().lstrip(",").strip()
        try:
            action = int(action_part)
        except ValueError:
            continue
        # Parse the state tuple from its string representation
        # e.g. "('left', 'none', 'high', 'low', 'low', 'low')"
        try:
            state_tuple = eval(state_part)  # noqa: S307
        except Exception:
            continue
        parsed[(state_tuple, action)] = float(value)

    return parsed


def _qtable_best_actions(parsed):
    """Return {state_tuple: best_action_index} from parsed Q-table."""
    # Group by state, find argmax action
    state_actions = defaultdict(dict)
    for (state, action), qval in parsed.items():
        state_actions[state][action] = qval

    best = {}
    for state, actions in state_actions.items():
        best[state] = max(actions, key=actions.get)
    return best


# ---------------------------------------------------------------------------
# Chart: heatmap_policy.png
# ---------------------------------------------------------------------------
def chart_heatmap_policy(qtable_path, output_dir):
    """Policy heatmap: most common best action per (battery_level, cat_danger)."""
    parsed = _parse_qtable(qtable_path)
    if not parsed:
        return None

    best_actions = _qtable_best_actions(parsed)

    # State tuple structure: (dirt_direction, cat_direction, battery_level,
    #                         cat_danger, dirt_density, exploration_status)
    # We want battery_level (index 2) and cat_danger (index 3)
    battery_levels = ["high", "medium", "low"]
    cat_danger_levels = ["low", "medium", "high"]

    # For each (battery, cat_danger), count best actions
    grid = {}
    for (bat, cat) in [(b, c) for b in battery_levels for c in cat_danger_levels]:
        action_counts = Counter()
        for state, action in best_actions.items():
            if len(state) >= 4 and state[2] == bat and state[3] == cat:
                action_counts[action] += 1
        if action_counts:
            grid[(bat, cat)] = action_counts.most_common(1)[0][0]
        else:
            grid[(bat, cat)] = -1  # no data

    # Build the heatmap matrix
    n_actions = len(ACTION_NAMES)
    # Colour map: one colour per action
    action_colors = ["#4C72B0", "#DD8452", "#55A868", "#C44E52", "#8172B3"]
    # Extend if more actions than colours
    while len(action_colors) < n_actions:
        action_colors.append("#999999")

    fig, ax = plt.subplots(figsize=(8, 5))
    matrix = np.zeros((len(battery_levels), len(cat_danger_levels)), dtype=int)
    for i, bat in enumerate(battery_levels):
        for j, cat in enumerate(cat_danger_levels):
            act = grid.get((bat, cat), -1)
            matrix[i, j] = act if act >= 0 else 0

    # Use imshow with discrete colour boundaries
    from matplotlib.colors import ListedColormap, BoundaryNorm
    cmap = ListedColormap(action_colors[:n_actions])
    bounds = list(range(n_actions + 1))
    norm = BoundaryNorm(bounds, cmap.N)

    im = ax.imshow(matrix, cmap=cmap, norm=norm, aspect="auto")

    # Annotate cells with action names
    for i in range(len(battery_levels)):
        for j in range(len(cat_danger_levels)):
            act = grid.get((battery_levels[i], cat_danger_levels[j]), -1)
            label = ACTION_NAMES[act] if 0 <= act < len(ACTION_NAMES) else "N/A"
            ax.text(j, i, label, ha="center", va="center", fontsize=10,
                    fontweight="bold", color="white")

    ax.set_xticks(range(len(cat_danger_levels)))
    ax.set_xticklabels(cat_danger_levels)
    ax.set_yticks(range(len(battery_levels)))
    ax.set_yticklabels(battery_levels)
    ax.set_xlabel("Cat Danger Level", fontsize=12)
    ax.set_ylabel("Battery Level", fontsize=12)
    ax.set_title("Q-Learning Learned Policy Summary", fontsize=14, pad=12)

    path = Path(output_dir) / "heatmap_policy.png"
    _savefig(fig, path)
    return str(path)


# ---------------------------------------------------------------------------
# Chart: bar_action_distribution.png
# ---------------------------------------------------------------------------
def chart_bar_action_distribution(qtable_path, output_dir):
    """Bar chart: how many states prefer each action."""
    parsed = _parse_qtable(qtable_path)
    if not parsed:
        return None

    best_actions = _qtable_best_actions(parsed)

    counts = Counter(best_actions.values())
    # Build ordered counts for each action
    actions = list(range(len(ACTION_NAMES)))
    values = [counts.get(a, 0) for a in actions]

    fig, ax = plt.subplots(figsize=(10, 6))
    colors = ["#4C72B0", "#DD8452", "#55A868", "#C44E52", "#8172B3"]
    while len(colors) < len(actions):
        colors.append("#999999")

    x = np.arange(len(actions))
    ax.bar(x, values, color=colors[:len(actions)], edgecolor="white", width=0.55)
    ax.set_xticks(x)
    ax.set_xticklabels(ACTION_NAMES, rotation=15, ha="right")
    _style_ax(ax, "Q-Learning Action Distribution Across States",
              "Number of States", "Action")

    path = Path(output_dir) / "bar_action_distribution.png"
    _savefig(fig, path)
    return str(path)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Generate analysis charts from experiment CSV results."
    )
    parser.add_argument(
        "--comparison",
        type=str,
        default=None,
        help="Path to comparison.csv",
    )
    parser.add_argument(
        "--training",
        type=str,
        default=None,
        help="Path to training_curve.csv",
    )
    parser.add_argument(
        "--cat-gradient",
        type=str,
        default=None,
        help="Path to cat_gradient.csv",
    )
    parser.add_argument(
        "--training-duration",
        type=str,
        default=None,
        help="Path to training_duration.csv",
    )
    parser.add_argument(
        "--qtable",
        type=str,
        default=None,
        help="Path to trained Q-table JSON file (trained.json)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="experiments/figures/",
        help="Directory for generated figures",
    )
    args = parser.parse_args(argv)

    # --- dependency check ---------------------------------------------------
    if not HAS_MPL:
        print("ERROR: matplotlib is required but not installed.", file=sys.stderr)
        print("Install with: pip install matplotlib", file=sys.stderr)
        return 1
    if not HAS_NP:
        print("ERROR: numpy is required but not installed.", file=sys.stderr)
        print("Install with: pip install numpy", file=sys.stderr)
        return 1

    _apply_style()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    generated = []

    # --- comparison charts --------------------------------------------------
    if args.comparison and Path(args.comparison).is_file():
        print(f"Reading comparison data from {args.comparison}")
        comp_rows = read_comparison_csv(args.comparison)

        for name, fn in [
            ("bar_dirt_collected.png", chart_bar_dirt_collected),
            ("box_collection_rate.png", chart_box_collection_rate),
            ("bar_cat_freezes.png", chart_bar_cat_freezes),
            ("bar_battery.png", chart_bar_battery),
            ("radar_comparison.png", chart_radar_comparison),
        ]:
            try:
                result = fn(comp_rows, output_dir)
                if result:
                    generated.append(result)
            except Exception as exc:
                print(f"  WARNING: could not generate {name}: {exc}", file=sys.stderr)

        try:
            result = generate_stats_summary(comp_rows, output_dir)
            if result:
                generated.append(result)
        except Exception as exc:
            print(f"  WARNING: could not generate stats_summary.txt: {exc}", file=sys.stderr)
    elif args.comparison:
        print(f"WARNING: comparison file not found: {args.comparison}", file=sys.stderr)

    # --- training curve charts ----------------------------------------------
    if args.training and Path(args.training).is_file():
        print(f"Reading training data from {args.training}")
        train_rows = read_training_csv(args.training)

        for name, fn in [
            ("training_curve_reward.png", chart_training_reward),
            ("training_curve_dirt.png", chart_training_dirt),
        ]:
            try:
                result = fn(train_rows, output_dir)
                if result:
                    generated.append(result)
            except Exception as exc:
                print(f"  WARNING: could not generate {name}: {exc}", file=sys.stderr)
    elif args.training:
        print(f"WARNING: training file not found: {args.training}", file=sys.stderr)

    # --- cat gradient charts ------------------------------------------------
    if args.cat_gradient and Path(args.cat_gradient).is_file():
        print(f"Reading cat gradient data from {args.cat_gradient}")
        cat_grad_rows = read_cat_gradient_csv(args.cat_gradient)

        for name, fn in [
            ("line_cat_gradient.png", chart_line_cat_gradient),
            ("line_cat_gradient_rate.png", chart_line_cat_gradient_rate),
        ]:
            try:
                result = fn(cat_grad_rows, output_dir)
                if result:
                    generated.append(result)
            except Exception as exc:
                print(f"  WARNING: could not generate {name}: {exc}", file=sys.stderr)
    elif args.cat_gradient:
        print(f"WARNING: cat gradient file not found: {args.cat_gradient}", file=sys.stderr)

    # --- training duration chart --------------------------------------------
    if args.training_duration and Path(args.training_duration).is_file():
        print(f"Reading training duration data from {args.training_duration}")
        td_rows = read_training_duration_csv(args.training_duration)

        # Attempt to load comparison rows for baseline lines
        comp_rows_for_baseline = None
        if args.comparison and Path(args.comparison).is_file():
            try:
                comp_rows_for_baseline = read_comparison_csv(args.comparison)
            except Exception:
                pass

        try:
            result = chart_line_training_duration(td_rows, output_dir, comp_rows_for_baseline)
            if result:
                generated.append(result)
        except Exception as exc:
            print(f"  WARNING: could not generate line_training_duration.png: {exc}",
                  file=sys.stderr)
    elif args.training_duration:
        print(f"WARNING: training duration file not found: {args.training_duration}",
              file=sys.stderr)

    # --- Q-table visualisation charts ---------------------------------------
    if args.qtable and Path(args.qtable).is_file():
        print(f"Reading Q-table from {args.qtable}")

        for name, fn in [
            ("heatmap_policy.png", chart_heatmap_policy),
            ("bar_action_distribution.png", chart_bar_action_distribution),
        ]:
            try:
                result = fn(args.qtable, output_dir)
                if result:
                    generated.append(result)
            except Exception as exc:
                print(f"  WARNING: could not generate {name}: {exc}", file=sys.stderr)
    elif args.qtable:
        print(f"WARNING: Q-table file not found: {args.qtable}", file=sys.stderr)

    # --- summary ------------------------------------------------------------
    if generated:
        print(f"\nGenerated {len(generated)} output(s):")
        for p in generated:
            print(f"  {p}")
    else:
        print("No charts generated. Provide --comparison and/or --training CSV paths.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
