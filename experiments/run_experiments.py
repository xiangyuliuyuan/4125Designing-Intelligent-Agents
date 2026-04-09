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


def run_single(brain_type, seed, frames, qtable_path=None, noOfCats=None, noOfBots=None):
    """Run one simulation and return metrics."""
    runtime.reset()
    runtime.simulation_tick = 0
    random.seed(seed)

    canvas = FakeCanvas()
    stats_vars = make_stats_vars()

    sim_data = create_simulation_data(canvas, brain_type=brain_type, noOfCats=noOfCats, noOfBots=noOfBots)
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


def run_comparison(brain_types, seeds, frames, qtable_path, output):
    """Run the default comparison experiment across brain types."""
    results = []
    total_runs = len(brain_types) * seeds
    run_count = 0

    for brain_type in brain_types:
        for seed in range(seeds):
            run_count += 1
            qtable = qtable_path if brain_type == "qlearning" else None
            print(f"[{run_count}/{total_runs}] {brain_type} seed={seed}...",
                  end=" ", flush=True)

            result = run_single(brain_type, seed=seed, frames=frames,
                                qtable_path=qtable)
            results.append(result)
            print(f"dirt={result['dirt_collected']}")

    # Write CSV
    fieldnames = ["brain_type", "seed", "frames", "dirt_collected",
                  "collection_rate", "cat_freeze_count", "battery_depletions"]
    with open(output, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print(f"\nResults saved to {output}")

    # Print summary
    print("\n=== Summary ===")
    for bt in brain_types:
        bt_results = [r for r in results if r["brain_type"] == bt]
        if not bt_results:
            continue
        dirts = [r["dirt_collected"] for r in bt_results]
        mean_d = sum(dirts) / len(dirts)
        std_d = (sum((d - mean_d) ** 2 for d in dirts) / len(dirts)) ** 0.5
        print(f"{bt:20s}: dirt={mean_d:.1f} +/- {std_d:.1f}")


def run_cat_gradient(brain_types, seeds, frames, cat_counts, qtable_path, output):
    """Run experiments varying cat count."""
    results = []
    total_runs = len(brain_types) * len(cat_counts) * seeds
    run_count = 0

    for brain_type in brain_types:
        for n_cats in cat_counts:
            for seed in range(seeds):
                run_count += 1
                qtable = qtable_path if brain_type == "qlearning" else None
                print(f"[{run_count}/{total_runs}] {brain_type} cats={n_cats} seed={seed}...",
                      end=" ", flush=True)

                result = run_single(brain_type, seed=seed, frames=frames,
                                    qtable_path=qtable, noOfCats=n_cats)
                result["cat_count"] = n_cats
                results.append(result)
                print(f"dirt={result['dirt_collected']}")

    # Write CSV with extra column "cat_count"
    fieldnames = ["brain_type", "seed", "frames", "cat_count", "dirt_collected",
                  "collection_rate", "cat_freeze_count", "battery_depletions"]
    with open(output, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print(f"\nResults saved to {output}")

    # Print summary
    print("\n=== Cat Gradient Summary ===")
    for bt in brain_types:
        for n_cats in cat_counts:
            subset = [r for r in results
                      if r["brain_type"] == bt and r["cat_count"] == n_cats]
            if not subset:
                continue
            dirts = [r["dirt_collected"] for r in subset]
            mean_d = sum(dirts) / len(dirts)
            std_d = (sum((d - mean_d) ** 2 for d in dirts) / len(dirts)) ** 0.5
            print(f"{bt:20s} cats={n_cats}: dirt={mean_d:.1f} +/- {std_d:.1f}")


def run_training_duration(brain_types, seeds, frames, training_episodes_list, qtable_path, output):
    """Train Q-Learning at different episode counts and evaluate each."""
    from experiments.train_qlearning import train

    results = []
    total_runs = len(training_episodes_list) * seeds
    run_count = 0

    for ep_count in training_episodes_list:
        # Train a Q-table with this many episodes
        qtable_file = os.path.join(os.path.dirname(qtable_path),
                                   f"trained_ep{ep_count}.json")
        csv_train = os.path.join(os.path.dirname(output),
                                 f"training_curve_ep{ep_count}.csv")
        print(f"\n--- Training Q-Learning for {ep_count} episodes ---")
        train(episodes=ep_count, frames=frames, qtable_output=qtable_file,
              csv_output=csv_train)

        # Evaluate the trained model
        for seed in range(seeds):
            run_count += 1
            print(f"[{run_count}/{total_runs}] qlearning episodes={ep_count} seed={seed}...",
                  end=" ", flush=True)

            result = run_single("qlearning", seed=seed, frames=frames,
                                qtable_path=qtable_file)
            result["training_episodes"] = ep_count
            results.append(result)
            print(f"dirt={result['dirt_collected']}")

    # Write CSV with extra column "training_episodes"
    fieldnames = ["brain_type", "seed", "frames", "training_episodes",
                  "dirt_collected", "collection_rate", "cat_freeze_count",
                  "battery_depletions"]
    with open(output, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print(f"\nResults saved to {output}")

    # Print summary
    print("\n=== Training Duration Summary ===")
    for ep_count in training_episodes_list:
        subset = [r for r in results if r["training_episodes"] == ep_count]
        if not subset:
            continue
        dirts = [r["dirt_collected"] for r in subset]
        mean_d = sum(dirts) / len(dirts)
        std_d = (sum((d - mean_d) ** 2 for d in dirts) / len(dirts)) ** 0.5
        print(f"episodes={ep_count:4d}: dirt={mean_d:.1f} +/- {std_d:.1f}")


def main():
    parser = argparse.ArgumentParser(description="Run batch comparison experiments")
    parser.add_argument("--experiment-type", default="comparison",
                        choices=["comparison", "cat_gradient", "training_duration"])
    parser.add_argument("--brain-types", nargs="+",
                        default=["subsumption", "potential_field", "qlearning"])
    parser.add_argument("--seeds", type=int, default=10)
    parser.add_argument("--frames", type=int, default=3000)
    parser.add_argument("--qtable", default="experiments/qtables/trained.json",
                        help="Path to trained Q-table for Q-Learning evaluation")
    parser.add_argument("--output", default=None,
                        help="Output CSV path (auto-determined from experiment type if omitted)")
    parser.add_argument("--cat-counts", nargs="+", type=int, default=[0, 2, 4, 6, 8])
    parser.add_argument("--training-episodes", nargs="+", type=int,
                        default=[25, 50, 100, 150, 200])
    args = parser.parse_args()

    # Determine output path
    output_defaults = {
        "comparison": "experiments/results/comparison.csv",
        "cat_gradient": "experiments/results/cat_gradient.csv",
        "training_duration": "experiments/results/training_duration.csv",
    }
    output = args.output or output_defaults[args.experiment_type]
    os.makedirs(os.path.dirname(output), exist_ok=True)

    configure_logging(log_filename="experiments.log", file_level="WARNING",
                      console_level="ERROR", reset=True)

    if args.experiment_type == "comparison":
        run_comparison(args.brain_types, args.seeds, args.frames, args.qtable, output)
    elif args.experiment_type == "cat_gradient":
        run_cat_gradient(args.brain_types, args.seeds, args.frames,
                         args.cat_counts, args.qtable, output)
    elif args.experiment_type == "training_duration":
        run_training_duration(args.brain_types, args.seeds, args.frames,
                              args.training_episodes, args.qtable, output)

    reset_logging()


if __name__ == "__main__":
    main()
