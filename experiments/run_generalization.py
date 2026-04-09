#!/usr/bin/env python3
"""Test generalization: train on standard, evaluate on different configs."""
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
from experiments.train_qlearning import train


CONFIGS = {
    "standard":   {"noOfCats": 4, "noOfBots": 3},   # Training environment
    "single_bot": {"noOfCats": 4, "noOfBots": 1},   # Can Q-Learning work alone?
    "many_bots":  {"noOfCats": 4, "noOfBots": 5},   # Does it scale to more agents?
    "hard_mode":  {"noOfCats": 8, "noOfBots": 1},   # Hardest: alone with many cats
}


def run_single(brain_type, seed, frames, config_name, qtable_path=None):
    """Run one simulation with given config and return metrics."""
    runtime.reset()
    runtime.simulation_tick = 0
    random.seed(seed)

    config = CONFIGS[config_name]
    canvas = FakeCanvas()
    stats_vars = make_stats_vars()

    sim_data = create_simulation_data(canvas, brain_type=brain_type,
                                      noOfCats=config.get("noOfCats", 4),
                                      noOfBots=config.get("noOfBots", 3))
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
    parser = argparse.ArgumentParser(
        description="Test generalization: train on standard, evaluate on different configs.")
    parser.add_argument("--seeds", type=int, default=10)
    parser.add_argument("--frames", type=int, default=1500)
    parser.add_argument("--training-episodes", type=int, default=200)
    parser.add_argument("--training-frames", type=int, default=1500)
    parser.add_argument("--qtable", default=None,
                        help="Skip training, use existing Q-table")
    parser.add_argument("--output",
                        default="experiments/results/generalization.csv")
    args = parser.parse_args()

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    configure_logging(log_filename="generalization.log", file_level="WARNING",
                      console_level="ERROR", reset=True)

    # Step 1: Train on standard (or use existing Q-table)
    qtable_path = args.qtable
    if not qtable_path:
        print("=== Training Q-Learning on standard config ===")
        qtable_path = "experiments/qtables/trained_standard.json"
        train(episodes=args.training_episodes, frames=args.training_frames,
              seed=42, qtable_output=qtable_path,
              csv_output="experiments/results/generalization_training.csv")

    # Step 2: Evaluate all brain types on all configs
    results = []
    brain_types = ["subsumption", "potential_field", "qlearning"]
    configs = list(CONFIGS.keys())
    total = len(brain_types) * len(configs) * args.seeds
    count = 0

    for config_name in configs:
        for brain_type in brain_types:
            for seed in range(args.seeds):
                count += 1
                qt = qtable_path if brain_type == "qlearning" else None
                print(f"[{count}/{total}] {brain_type} @ {config_name} seed={seed}...",
                      end=" ", flush=True)
                result = run_single(brain_type, seed, args.frames,
                                    config_name, qt)
                result["config"] = config_name
                results.append(result)
                print(f"dirt={result['dirt_collected']}")

    # Step 3: Write CSV
    fieldnames = ["brain_type", "config", "seed", "frames", "dirt_collected",
                  "collection_rate", "cat_freeze_count", "battery_depletions"]
    with open(args.output, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    # Print summary
    print(f"\nResults saved to {args.output}")
    print("\n=== Generalization Results ===")
    for config_name in configs:
        print(f"\n--- {config_name} ---")
        for bt in brain_types:
            bt_results = [r for r in results
                          if r["brain_type"] == bt and r["config"] == config_name]
            dirts = [r["dirt_collected"] for r in bt_results]
            mean_d = sum(dirts) / len(dirts)
            print(f"  {bt:20s}: dirt={mean_d:.1f}")

    reset_logging()


if __name__ == "__main__":
    main()
