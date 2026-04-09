#!/usr/bin/env python3
"""Train a Q-Learning agent via headless simulation episodes."""
import argparse
import csv
import os
import random
import sys
import time
from pathlib import Path

# Project root on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from run_headless import FakeCanvas, make_stats_vars, WORLD_SIZE
from app.context import create_simulation_data
from app.logging_config import configure_logging, reset_logging
from simulation import runtime
from simulation.engine import advance_simulation_frame
from robot.brain_qlearning import QLearningBrain


def train(episodes=300, frames=2000, alpha=0.1, gamma=0.95,
          epsilon_start=1.0, epsilon_end=0.05, seed=42,
          qtable_output="experiments/qtables/trained.json",
          csv_output="experiments/results/training_curve.csv"):

    os.makedirs(os.path.dirname(qtable_output), exist_ok=True)
    os.makedirs(os.path.dirname(csv_output), exist_ok=True)

    # Configure minimal logging (suppress most output)
    configure_logging(log_filename="training.log", file_level="WARNING",
                      console_level="ERROR", reset=True)

    # Shared Q-table across episodes (persists learning)
    shared_qtable = None
    epsilon = epsilon_start
    # Linear epsilon decay
    epsilon_decay_per_episode = (epsilon_start - epsilon_end) / max(episodes - 1, 1)

    csv_rows = []

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

        # Setup Q-Learning brains with shared Q-table
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

        prev_dirt = count.dirtCollected
        episode_reward = 0.0

        for frame in range(frames):
            runtime.simulation_tick += 1

            passive_objects, snapshot = advance_simulation_frame(
                canvas, agents, passive_objects, count, cats,
                debris_count, stats_vars, start_time, chargers,
                dt=1.0, now=start_time + runtime.simulation_tick
            )

            # Calculate reward
            new_dirt = count.dirtCollected
            dirt_delta = new_dirt - prev_dirt
            prev_dirt = new_dirt

            for brain in ql_brains:
                reward = -0.1  # time penalty
                if dirt_delta > 0:
                    reward += 10.0 * dirt_delta
                # Check battery depletion
                bot = brain.bot
                if bot.battery <= 0:
                    reward -= 50.0
                brain.give_reward(reward)
                episode_reward += reward

        # End episode
        for brain in ql_brains:
            brain.end_episode()

        # Decay epsilon (linear)
        epsilon = max(epsilon_end, epsilon - epsilon_decay_per_episode)

        # Save Q-table from first brain (they share)
        if ql_brains:
            shared_qtable = dict(ql_brains[0].q_table)

        dirt_collected = count.dirtCollected
        csv_rows.append({
            "episode": ep,
            "total_reward": round(episode_reward, 2),
            "dirt_collected": dirt_collected,
            "epsilon": round(epsilon, 4)
        })

        if ep % 50 == 0 or ep == episodes - 1:
            print(f"Episode {ep}/{episodes}: reward={episode_reward:.1f}, "
                  f"dirt={dirt_collected}, epsilon={epsilon:.3f}")

    # Save Q-table
    if ql_brains:
        ql_brains[0].q_table = shared_qtable or ql_brains[0].q_table
        ql_brains[0].save_qtable(qtable_output)
        print(f"Q-table saved to {qtable_output} ({len(shared_qtable)} entries)")

    # Save CSV
    with open(csv_output, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["episode", "total_reward", "dirt_collected", "epsilon"])
        writer.writeheader()
        writer.writerows(csv_rows)
    print(f"Training curve saved to {csv_output}")

    reset_logging()


def main():
    parser = argparse.ArgumentParser(description="Train Q-Learning agent")
    parser.add_argument("--episodes", type=int, default=300)
    parser.add_argument("--frames", type=int, default=2000)
    parser.add_argument("--alpha", type=float, default=0.1)
    parser.add_argument("--gamma", type=float, default=0.95)
    parser.add_argument("--epsilon-start", type=float, default=1.0)
    parser.add_argument("--epsilon-end", type=float, default=0.05)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", default="experiments/qtables/trained.json")
    parser.add_argument("--log-csv", default="experiments/results/training_curve.csv")
    args = parser.parse_args()

    train(
        episodes=args.episodes, frames=args.frames,
        alpha=args.alpha, gamma=args.gamma,
        epsilon_start=args.epsilon_start, epsilon_end=args.epsilon_end,
        seed=args.seed, qtable_output=args.output, csv_output=args.log_csv
    )


if __name__ == "__main__":
    main()
