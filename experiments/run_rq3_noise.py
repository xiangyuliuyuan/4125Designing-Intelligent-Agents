#!/usr/bin/env python3
"""RQ3: How sensitive is each agent architecture to sensor noise?"""
import argparse
import csv
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.logging_config import configure_logging, reset_logging
from robot.sensing import set_noise_sigma
from experiments.run_experiments import run_single


def main():
    parser = argparse.ArgumentParser(description="RQ3: Sensor noise robustness experiment")
    parser.add_argument("--brain-types", nargs="+",
                        default=["subsumption", "potential_field", "qlearning"])
    parser.add_argument("--noise-levels", nargs="+", type=float,
                        default=[0.0, 0.1, 0.2, 0.3, 0.5, 1.0])
    parser.add_argument("--seeds", type=int, default=10)
    parser.add_argument("--frames", type=int, default=1500)
    parser.add_argument("--qtable", default="experiments/qtables/trained.json")
    parser.add_argument("--output", default="experiments/results/rq3_noise.csv")
    args = parser.parse_args()

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    configure_logging(log_filename="rq3.log", file_level="WARNING",
                      console_level="ERROR", reset=True)

    results = []
    total = len(args.brain_types) * len(args.noise_levels) * args.seeds
    run_count = 0

    for brain_type in args.brain_types:
        for sigma in args.noise_levels:
            for seed in range(args.seeds):
                run_count += 1
                qtable = args.qtable if brain_type == "qlearning" else None
                print(f"[{run_count}/{total}] {brain_type} noise={sigma} seed={seed}...",
                      end=" ", flush=True)

                set_noise_sigma(sigma)
                try:
                    result = run_single(brain_type, seed=seed, frames=args.frames,
                                        qtable_path=qtable)
                finally:
                    set_noise_sigma(0.0)

                result["noise_sigma"] = sigma
                results.append(result)
                print(f"dirt={result['dirt_collected']}")

    fieldnames = ["brain_type", "seed", "frames", "noise_sigma", "dirt_collected",
                  "collection_rate", "cat_freeze_count", "battery_depletions"]
    with open(args.output, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print(f"\nResults saved to {args.output}")

    # Summary
    print("\n=== RQ3 Noise Robustness Summary ===")
    for bt in args.brain_types:
        print(f"\n--- {bt} ---")
        for sigma in args.noise_levels:
            subset = [r for r in results
                      if r["brain_type"] == bt and r["noise_sigma"] == sigma]
            if not subset:
                continue
            dirts = [r["dirt_collected"] for r in subset]
            mean_d = sum(dirts) / len(dirts)
            print(f"  sigma={sigma:.1f}: dirt={mean_d:.1f}")

    reset_logging()


if __name__ == "__main__":
    main()
