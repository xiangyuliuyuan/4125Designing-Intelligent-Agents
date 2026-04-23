#!/usr/bin/env python3
"""RQ4: How do different reward functions affect Q-Learning performance?"""
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
from robot.sensing import sense_light
from experiments.run_experiments import run_single
from experiments.utils import count_transitions as _count_transitions

REWARD_TYPES = ["baseline", "heavy_safety", "dense_progress", "energy_aware", "sparse"]


def train_with_reward(reward_type, episodes=200, frames=1500, alpha=0.1, gamma=0.95,
                      epsilon_start=1.0, epsilon_end=0.05, seed=42,
                      qtable_output=None, csv_output=None):
    """Train Q-Learning with a specified reward function variant."""
    from collections import defaultdict

    os.makedirs(os.path.dirname(qtable_output), exist_ok=True)
    os.makedirs(os.path.dirname(csv_output), exist_ok=True)
    configure_logging(log_filename="rq4_training.log", file_level="WARNING",
                      console_level="ERROR", reset=True)

    shared_qtable = None
    epsilon = epsilon_start
    epsilon_decay_per_episode = (epsilon_start - epsilon_end) / max(episodes - 1, 1)
    csv_rows = []
    ql_brains = []

    for ep in range(episodes):
        runtime.reset()
        runtime.simulation_tick = 0
        random.seed(seed + ep)

        canvas = FakeCanvas()
        stats_vars = make_stats_vars()
        sim_data = create_simulation_data(canvas, brain_type="qlearning")
        agents = sim_data["agents"]
        passive_objects = sim_data["passiveObjects"]
        count = sim_data["count"]
        cats = sim_data["cats"]
        debris_count = sim_data["debris_count"]
        chargers = sim_data["chargers"]
        start_time = sim_data["start_time"]

        ql_brains = []
        for agent in agents:
            if hasattr(agent, 'brain') and isinstance(agent.brain, QLearningBrain):
                agent.brain.alpha = alpha
                agent.brain.gamma = gamma
                agent.brain.epsilon = epsilon
                agent.brain.training = True
                if shared_qtable is not None:
                    agent.brain.q_table.update(shared_qtable)
                ql_brains.append(agent.brain)

        # Wrap collectDirt for per-bot tracking
        for agent in agents:
            agent._personal_dirt_delta = 0
            original_collect = agent.collectDirt
            def _make_wrapper(ag, orig):
                def wrapper(canvas, passiveObjects, cnt, debris_cnt, current_time=None):
                    before = cnt.dirtCollected
                    result = orig(canvas, passiveObjects, cnt, debris_cnt, current_time=current_time)
                    ag._personal_dirt_delta += cnt.dirtCollected - before
                    return result
                return wrapper
            agent.collectDirt = _make_wrapper(agent, original_collect)

        episode_reward = 0.0
        depleted_bots = set()
        frozen_bots = set()
        # For dense_progress: track previous light signals
        prev_light = {id(b): 0.0 for b in ql_brains}

        for frame in range(frames):
            runtime.simulation_tick += 1
            for agent in agents:
                agent._personal_dirt_delta = 0

            passive_objects, snapshot = advance_simulation_frame(
                canvas, agents, passive_objects, count, cats,
                debris_count, stats_vars, start_time, chargers,
                dt=1.0, now=start_time + runtime.simulation_tick
            )

            for brain in ql_brains:
                bot = brain.bot
                bot_dirt = getattr(bot, '_personal_dirt_delta', 0)

                # --- Compute reward based on reward_type ---
                if reward_type == "baseline":
                    reward = -0.1
                    if bot_dirt > 0:
                        reward += 10.0 * bot_dirt
                    if bot.battery <= 0 and bot.name not in depleted_bots:
                        reward -= 20.0
                        depleted_bots.add(bot.name)

                elif reward_type == "heavy_safety":
                    reward = -0.1
                    if bot_dirt > 0:
                        reward += 10.0 * bot_dirt
                    if bot.battery <= 0 and bot.name not in depleted_bots:
                        reward -= 20.0
                        depleted_bots.add(bot.name)
                    # Continuous cat proximity penalty (every frame near cat)
                    if getattr(brain, 'isAvoidingCat', False):
                        reward -= 5.0
                    if getattr(brain, 'is_cat_frozen', False):
                        reward -= 20.0

                elif reward_type == "dense_progress":
                    reward = -0.1
                    if bot_dirt > 0:
                        reward += 10.0 * bot_dirt
                    if bot.battery <= 0 and bot.name not in depleted_bots:
                        reward -= 20.0
                        depleted_bots.add(bot.name)
                    # Bonus for approaching light (dirt)
                    sensor_pos = bot.sensorPositions
                    lL, lR = sense_light(sensor_pos, passive_objects)
                    curr_light = lL + lR
                    bid = id(brain)
                    if curr_light > prev_light.get(bid, 0) + 10:
                        reward += 2.0
                    prev_light[bid] = curr_light

                elif reward_type == "energy_aware":
                    reward = -0.1
                    if bot_dirt > 0:
                        reward += 10.0 * bot_dirt
                    if bot.battery <= 0 and bot.name not in depleted_bots:
                        reward -= 20.0
                        depleted_bots.add(bot.name)
                    # Bonus for proactive charging + penalty for low battery
                    if getattr(bot, 'actively_charging', False):
                        reward += 5.0
                    if bot.battery < 300:
                        reward -= 3.0  # stronger penalty for very low battery

                elif reward_type == "sparse":
                    reward = 0.0
                    if bot_dirt > 0:
                        reward += 10.0 * bot_dirt

                brain.give_reward(reward)
                episode_reward += reward

        # End episode
        for brain in ql_brains:
            brain.end_episode()

        epsilon = max(epsilon_end, epsilon - epsilon_decay_per_episode)

        # Merge Q-tables
        if ql_brains:
            merged = {}
            counts_m = {}
            for brain in ql_brains:
                for key, val in brain.q_table.items():
                    if key in merged:
                        merged[key] += val
                        counts_m[key] += 1
                    else:
                        merged[key] = val
                        counts_m[key] = 1
            shared_qtable = defaultdict(float, {k: v / counts_m[k] for k, v in merged.items()})

        csv_rows.append({
            "episode": ep,
            "reward_type": reward_type,
            "total_reward": round(episode_reward, 2),
            "dirt_collected": count.dirtCollected,
            "epsilon": round(epsilon, 4)
        })

        if ep % 50 == 0 or ep == episodes - 1:
            print(f"  Episode {ep}/{episodes}: reward={episode_reward:.1f}, "
                  f"dirt={count.dirtCollected}, eps={epsilon:.3f}")

    # Save Q-table
    if ql_brains:
        ql_brains[0].q_table = shared_qtable or ql_brains[0].q_table
        ql_brains[0].save_qtable(qtable_output)
        entries = len(shared_qtable) if shared_qtable else len(ql_brains[0].q_table)
        print(f"  Q-table saved: {qtable_output} ({entries} entries)")

    # Save training CSV
    with open(csv_output, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["episode", "reward_type",
                                                "total_reward", "dirt_collected", "epsilon"])
        writer.writeheader()
        writer.writerows(csv_rows)

    reset_logging()
    return csv_rows


def main():
    parser = argparse.ArgumentParser(description="RQ4: Reward function comparison")
    parser.add_argument("--reward-types", nargs="+", default=REWARD_TYPES)
    parser.add_argument("--training-episodes", type=int, default=200)
    parser.add_argument("--seeds", type=int, default=10)
    parser.add_argument("--frames", type=int, default=1500)
    parser.add_argument("--output", default="experiments/results/rq4_rewards.csv")
    args = parser.parse_args()

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    configure_logging(log_filename="rq4.log", file_level="WARNING",
                      console_level="ERROR", reset=True)

    all_training_rows = []

    # Step 1: Train each reward variant (different base seed per variant)
    for idx, reward_type in enumerate(args.reward_types):
        print(f"\n=== Training: {reward_type} ({args.training_episodes} episodes) ===")
        qtable_path = f"experiments/qtables/trained_{reward_type}.json"
        csv_path = f"experiments/results/rq4_training_{reward_type}.csv"
        variant_seed = 42 + idx * 1000
        rows = train_with_reward(
            reward_type,
            episodes=args.training_episodes,
            frames=args.frames,
            seed=variant_seed,
            qtable_output=qtable_path,
            csv_output=csv_path,
        )
        all_training_rows.extend(rows)

    # Step 2: Evaluate each trained variant
    results = []
    total = len(args.reward_types) * args.seeds + args.seeds  # + subsumption baseline
    run_count = 0

    # Subsumption baseline
    for seed in range(args.seeds):
        run_count += 1
        print(f"[{run_count}/{total}] subsumption_baseline seed={seed}...",
              end=" ", flush=True)
        result = run_single("subsumption", seed=seed, frames=args.frames)
        result["reward_type"] = "subsumption_baseline"
        results.append(result)
        print(f"dirt={result['dirt_collected']}")

    # Q-Learning variants
    for reward_type in args.reward_types:
        qtable_path = f"experiments/qtables/trained_{reward_type}.json"
        for seed in range(args.seeds):
            run_count += 1
            print(f"[{run_count}/{total}] {reward_type} seed={seed}...",
                  end=" ", flush=True)
            result = run_single("qlearning", seed=seed, frames=args.frames,
                                qtable_path=qtable_path)
            result["reward_type"] = reward_type
            results.append(result)
            print(f"dirt={result['dirt_collected']}")

    # Write evaluation CSV
    fieldnames = ["reward_type", "brain_type", "seed", "frames", "dirt_collected",
                  "collection_rate", "cat_freeze_count", "battery_depletions"]
    with open(args.output, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    # Write combined training CSV
    training_output = "experiments/results/rq4_training_all.csv"
    with open(training_output, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["episode", "reward_type",
                                                "total_reward", "dirt_collected", "epsilon"])
        writer.writeheader()
        writer.writerows(all_training_rows)

    print(f"\nEvaluation results saved to {args.output}")
    print(f"Training curves saved to {training_output}")

    # Summary
    print("\n=== RQ4 Reward Comparison Summary ===")
    for rt in ["subsumption_baseline"] + args.reward_types:
        subset = [r for r in results if r["reward_type"] == rt]
        if not subset:
            continue
        dirts = [r["dirt_collected"] for r in subset]
        freezes = [r["cat_freeze_count"] for r in subset]
        mean_d = sum(dirts) / len(dirts)
        mean_f = sum(freezes) / len(freezes)
        print(f"  {rt:20s}: dirt={mean_d:.1f}  freezes={mean_f:.1f}")

    reset_logging()


if __name__ == "__main__":
    main()
