#!/usr/bin/env python3
"""RQ2: How does cleaning performance scale with the number of robots?"""
import argparse
import csv
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.logging_config import configure_logging, reset_logging
from experiments.run_experiments import run_single


def main():
    parser = argparse.ArgumentParser(description="RQ2: Robot count scaling experiment")
    parser.add_argument("--brain-types", nargs="+",
                        default=["subsumption", "potential_field", "qlearning"])
    parser.add_argument("--bot-counts", nargs="+", type=int,
                        default=[1, 2, 3, 5, 7, 10])
    parser.add_argument("--seeds", type=int, default=10)
    parser.add_argument("--frames", type=int, default=1500)
    parser.add_argument("--qtable", default="experiments/qtables/trained.json")
    parser.add_argument("--output", default="experiments/results/rq2_scaling.csv")
    args = parser.parse_args()

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    configure_logging(log_filename="rq2.log", file_level="WARNING",
                      console_level="ERROR", reset=True)

    results = []
    total = len(args.brain_types) * len(args.bot_counts) * args.seeds
    run_count = 0

    for brain_type in args.brain_types:
        for bot_count in args.bot_counts:
            for seed in range(args.seeds):
                run_count += 1
                qtable = args.qtable if brain_type == "qlearning" else None
                print(f"[{run_count}/{total}] {brain_type} bots={bot_count} seed={seed}...",
                      end=" ", flush=True)

                result = run_single(brain_type, seed=seed, frames=args.frames,
                                    qtable_path=qtable, noOfBots=bot_count)
                result["bot_count"] = bot_count
                result["dirt_per_bot"] = round(result["dirt_collected"] / bot_count, 4)
                results.append(result)
                print(f"dirt={result['dirt_collected']} (per_bot={result['dirt_per_bot']})")

    fieldnames = ["brain_type", "seed", "frames", "bot_count", "dirt_collected",
                  "collection_rate", "dirt_per_bot", "cat_freeze_count", "battery_depletions"]
    with open(args.output, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print(f"\nResults saved to {args.output}")

    # Summary
    print("\n=== RQ2 Scaling Summary ===")
    for bt in args.brain_types:
        print(f"\n--- {bt} ---")
        for bc in args.bot_counts:
            subset = [r for r in results
                      if r["brain_type"] == bt and r["bot_count"] == bc]
            if not subset:
                continue
            dirts = [r["dirt_collected"] for r in subset]
            per_bots = [r["dirt_per_bot"] for r in subset]
            mean_d = sum(dirts) / len(dirts)
            mean_pb = sum(per_bots) / len(per_bots)
            print(f"  bots={bc:2d}: total={mean_d:.1f}  per_bot={mean_pb:.1f}")

    reset_logging()


if __name__ == "__main__":
    main()
