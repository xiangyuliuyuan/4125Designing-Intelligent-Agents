#!/usr/bin/env python3
"""RQ5: Does spatial memory (coverage map) improve cleaning efficiency?"""
import argparse
import csv
import os
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from run_headless import FakeCanvas, make_stats_vars
from app.context import create_simulation_data
from app.logging_config import configure_logging, reset_logging
from simulation import runtime
from simulation.engine import advance_simulation_frame
from robot.brain_qlearning import QLearningBrain
from robot.brain_coverage import CoverageMapBrain
from experiments.utils import count_transitions as _count_transitions


def run_single_with_coverage(brain_type, seed, frames, qtable_path=None,
                             coverage_sample_interval=100):
    """Run one simulation and return metrics + coverage timeline."""
    runtime.reset()
    runtime.simulation_tick = 0
    random.seed(seed)

    canvas = FakeCanvas()
    stats_vars = make_stats_vars()

    sim_data = create_simulation_data(canvas, brain_type=brain_type)
    agents = sim_data["agents"]
    passive_objects = sim_data["passiveObjects"]
    count = sim_data["count"]
    cats = sim_data["cats"]
    debris_count = sim_data["debris_count"]
    chargers = sim_data["chargers"]
    start_time = sim_data["start_time"]

    if brain_type == "qlearning" and qtable_path and os.path.exists(qtable_path):
        for agent in agents:
            if hasattr(agent, 'brain') and isinstance(agent.brain, QLearningBrain):
                agent.brain.load_qtable(qtable_path)
                agent.brain.set_training(False)

    cat_freeze_count = 0
    battery_depletions = 0
    frozen_agents = set()
    depleted_agents = set()
    coverage_timeline = []
    # External coverage grid tracks all brain types equally
    ext_grid = [[0] * COVERAGE_GRID for _ in range(COVERAGE_GRID)]

    for frame in range(frames):
        runtime.simulation_tick += 1

        passive_objects, snapshot = advance_simulation_frame(
            canvas, agents, passive_objects, count, cats,
            debris_count, stats_vars, start_time, chargers,
            dt=1.0, now=start_time + runtime.simulation_tick
        )

        frame_freezes, frame_depletions, frozen_agents, depleted_agents = _count_transitions(
            agents, frozen_agents, depleted_agents,
        )
        cat_freeze_count += frame_freezes
        battery_depletions += frame_depletions

        # Track coverage for ALL brain types
        _update_external_grid(agents, ext_grid)

        # Sample coverage percentage
        if (frame + 1) % coverage_sample_interval == 0:
            cov_pct = _get_coverage(agents, ext_grid)
            coverage_timeline.append((frame + 1, cov_pct))

    dirt_collected = count.dirtCollected
    final_coverage = _get_coverage(agents, ext_grid)

    return {
        "brain_type": brain_type,
        "seed": seed,
        "frames": frames,
        "dirt_collected": dirt_collected,
        "collection_rate": round(dirt_collected / frames, 6),
        "cat_freeze_count": cat_freeze_count,
        "battery_depletions": battery_depletions,
        "final_coverage": round(final_coverage, 4),
    }, coverage_timeline


COVERAGE_GRID = 50
COVERAGE_CELL = 20  # 1000 / 50


def _get_coverage(agents, external_grid=None):
    """Get coverage percentage from an external grid tracking all agents."""
    if external_grid is None:
        return 0.0
    visited = sum(1 for row in external_grid for c in row if c > 0)
    return visited / (COVERAGE_GRID * COVERAGE_GRID)


def _update_external_grid(agents, grid):
    """Update external coverage grid from all agents' positions."""
    for agent in agents:
        gx = max(0, min(COVERAGE_GRID - 1, int(agent.x / COVERAGE_CELL)))
        gy = max(0, min(COVERAGE_GRID - 1, int(agent.y / COVERAGE_CELL)))
        grid[gy][gx] += 1


def main():
    parser = argparse.ArgumentParser(description="RQ5: Coverage map experiment")
    parser.add_argument("--brain-types", nargs="+",
                        default=["subsumption", "coverage", "qlearning"])
    parser.add_argument("--seeds", type=int, default=10)
    parser.add_argument("--short-frames", type=int, default=1500)
    parser.add_argument("--long-frames", type=int, default=5000)
    parser.add_argument("--qtable", default="experiments/qtables/trained.json")
    parser.add_argument("--output", default="experiments/results/rq5_coverage.csv")
    parser.add_argument("--coverage-output",
                        default="experiments/results/rq5_coverage_timeline.csv")
    args = parser.parse_args()

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    configure_logging(log_filename="rq5.log", file_level="WARNING",
                      console_level="ERROR", reset=True)

    durations = [
        ("short", args.short_frames),
        ("long", args.long_frames),
    ]

    results = []
    coverage_rows = []
    total = len(args.brain_types) * len(durations) * args.seeds
    run_count = 0

    for duration_type, frame_count in durations:
        for brain_type in args.brain_types:
            for seed in range(args.seeds):
                run_count += 1
                qtable = args.qtable if brain_type == "qlearning" else None
                print(f"[{run_count}/{total}] {brain_type} {duration_type} "
                      f"({frame_count}f) seed={seed}...", end=" ", flush=True)

                result, timeline = run_single_with_coverage(
                    brain_type, seed=seed, frames=frame_count,
                    qtable_path=qtable, coverage_sample_interval=100
                )
                result["duration_type"] = duration_type
                results.append(result)
                print(f"dirt={result['dirt_collected']} cov={result['final_coverage']:.2%}")

                for frame_num, cov_pct in timeline:
                    coverage_rows.append({
                        "brain_type": brain_type,
                        "duration_type": duration_type,
                        "seed": seed,
                        "frame": frame_num,
                        "coverage_pct": round(cov_pct, 4),
                    })

    # Write main results CSV
    fieldnames = ["brain_type", "duration_type", "seed", "frames", "dirt_collected",
                  "collection_rate", "cat_freeze_count", "battery_depletions",
                  "final_coverage"]
    with open(args.output, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    # Write coverage timeline CSV
    with open(args.coverage_output, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["brain_type", "duration_type",
                                                "seed", "frame", "coverage_pct"])
        writer.writeheader()
        writer.writerows(coverage_rows)

    print(f"\nResults saved to {args.output}")
    print(f"Coverage timeline saved to {args.coverage_output}")

    # Summary
    print("\n=== RQ5 Coverage Summary ===")
    for dt, _ in durations:
        print(f"\n--- {dt} ---")
        for bt in args.brain_types:
            subset = [r for r in results
                      if r["brain_type"] == bt and r["duration_type"] == dt]
            if not subset:
                continue
            dirts = [r["dirt_collected"] for r in subset]
            covs = [r["final_coverage"] for r in subset]
            mean_d = sum(dirts) / len(dirts)
            mean_c = sum(covs) / len(covs)
            print(f"  {bt:15s}: dirt={mean_d:.1f}  coverage={mean_c:.2%}")

    reset_logging()


if __name__ == "__main__":
    main()
