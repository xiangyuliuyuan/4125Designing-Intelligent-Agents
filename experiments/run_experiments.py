#!/usr/bin/env python3
"""Run batch experiments comparing different brain types."""
import argparse
import csv
import os
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from run_headless import FakeCanvas, make_stats_vars, WORLD_SIZE
from app.context import create_simulation_data
from app.logging_config import configure_logging, reset_logging
from simulation import runtime
from simulation.engine import advance_simulation_frame
from robot.brain_qlearning import QLearningBrain


def run_single(brain_type, seed, frames, qtable_path=None):
    """Run one simulation and return metrics."""
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

    # For Q-Learning: load trained Q-table and set to eval mode
    if brain_type == "qlearning" and qtable_path and os.path.exists(qtable_path):
        for agent in agents:
            if hasattr(agent, 'brain') and isinstance(agent.brain, QLearningBrain):
                agent.brain.load_qtable(qtable_path)
                agent.brain.set_training(False)

    cat_freeze_count = 0
    battery_depletions = 0

    for frame in range(frames):
        runtime.simulation_tick += 1

        passive_objects, snapshot = advance_simulation_frame(
            canvas, agents, passive_objects, count, cats,
            debris_count, stats_vars, start_time, chargers,
            dt=1.0, now=start_time + runtime.simulation_tick
        )

        # Track cat freezes and battery
        for agent in agents:
            if hasattr(agent, 'brain'):
                if getattr(agent.brain, 'is_cat_frozen', False):
                    cat_freeze_count += 1
            if agent.battery <= 0:
                battery_depletions += 1

    dirt_collected = count.dirtCollected

    return {
        "brain_type": brain_type,
        "seed": seed,
        "frames": frames,
        "dirt_collected": dirt_collected,
        "collection_rate": round(dirt_collected / frames, 6),
        "cat_freeze_count": cat_freeze_count,
        "battery_depletions": battery_depletions,
    }


def main():
    parser = argparse.ArgumentParser(description="Run batch comparison experiments")
    parser.add_argument("--brain-types", nargs="+",
                        default=["subsumption", "potential_field", "qlearning"])
    parser.add_argument("--seeds", type=int, default=10)
    parser.add_argument("--frames", type=int, default=3000)
    parser.add_argument("--qtable", default="experiments/qtables/trained.json",
                        help="Path to trained Q-table for Q-Learning evaluation")
    parser.add_argument("--output", default="experiments/results/comparison.csv")
    args = parser.parse_args()

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    configure_logging(log_filename="experiments.log", file_level="WARNING",
                      console_level="ERROR", reset=True)

    results = []
    total_runs = len(args.brain_types) * args.seeds
    run_count = 0

    for brain_type in args.brain_types:
        for seed in range(args.seeds):
            run_count += 1
            qtable = args.qtable if brain_type == "qlearning" else None
            print(f"[{run_count}/{total_runs}] {brain_type} seed={seed}...",
                  end=" ", flush=True)

            result = run_single(brain_type, seed=seed, frames=args.frames,
                                qtable_path=qtable)
            results.append(result)
            print(f"dirt={result['dirt_collected']}")

    # Write CSV
    fieldnames = ["brain_type", "seed", "frames", "dirt_collected",
                  "collection_rate", "cat_freeze_count", "battery_depletions"]
    with open(args.output, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print(f"\nResults saved to {args.output}")

    # Print summary
    print("\n=== Summary ===")
    for bt in args.brain_types:
        bt_results = [r for r in results if r["brain_type"] == bt]
        if not bt_results:
            continue
        dirts = [r["dirt_collected"] for r in bt_results]
        mean_d = sum(dirts) / len(dirts)
        std_d = (sum((d - mean_d) ** 2 for d in dirts) / len(dirts)) ** 0.5
        print(f"{bt:20s}: dirt={mean_d:.1f} +/- {std_d:.1f}")

    reset_logging()


if __name__ == "__main__":
    main()
