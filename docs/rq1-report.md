# Research Question 1: Three-Way Agent Architecture Comparison

> **Question**: How do three fundamentally different agent architectures — rule-based (Subsumption), reactive (Artificial Potential Field), and learning-based (Q-Learning) — compare in cleaning task performance, and what are their respective strengths and weaknesses?

This report has been refreshed after fixing several logic issues in the simulator and experiment pipeline:

- cat-safety behaviours now take priority over low-battery charging in the Subsumption and Coverage controllers
- A* charging paths now respect the simulator's toroidal world geometry
- cat-freeze and battery-depletion metrics are counted as transition events, including physical safety freezes
- the canonical Q-Learning policy has been retrained on the current codebase before evaluation

---

## 1. Background

The project compares three classic agent paradigms inside the same multi-robot cleaning simulator:

- **Subsumption Architecture**: a hand-designed priority stack of reactive behaviours
- **Artificial Potential Field (APF)**: attraction and repulsion forces combined into wheel-speed commands
- **Q-Learning**: a tabular reinforcement learner that maps discretised states to action values

These paradigms represent three different design philosophies: **hand-crafted rules**, **physics-inspired reaction**, and **experience-driven learning**.

## 2. Implementation

### 2.1 Subsumption Architecture (`robot/brain.py`)

The subsumption agent uses a 7-layer priority stack:

| Priority | Behaviour | Trigger |
|----------|-----------|---------|
| 1 (highest) | Overlap separation | Bot signal > 20,000 |
| 2 | Cat freeze | Cat signal > 3,000 |
| 3 | Cat avoidance | Cat signal > 700 |
| 4 | Low-battery charging (A* navigation) | Battery < 600 |
| 5 | Debris avoidance | Debris signal > 5,000 |
| 6 | Bot avoidance | Bot signal > 3,000 |
| 7 (lowest) | Random wandering | Default |

This ordering now matches the actual implementation: **cat safety overrides charging**.

### 2.2 Artificial Potential Field (`robot/brain_potential_field.py`)

Forces are computed from left/right sensor imbalance:

- **Attractive**: light signals plus charger attraction when battery is low (`10x` charger weight)
- **Repulsive**: cat signals (`8x`), debris signals (`4x`), and other bots (`1.5x`)

The resulting turn signal is mapped to differential wheel speeds. Hard cat freeze and hard debris avoidance still sit above the soft force blend.

### 2.3 Q-Learning (`robot/brain_qlearning.py`)

**State space** (6 features, discretised from sensor readings):

| Feature | Values | Discretisation |
|---------|--------|----------------|
| Light direction | left / right / balanced / none | Sensor signal ratio |
| Charger direction | left / right / balanced / none | Sensor signal ratio |
| Battery level | high / medium / low / critical | `>800` / `>600` / `>300` / else |
| Cat danger | high / medium / low | Sum `>3000` / `>700` / else |
| Debris danger | high / low | Sum `>5000` / else |
| Bot danger | high / low | Sum `>3000` / else |

**Action space** (7 actions): `FORWARD`, `TURN_LEFT`, `TURN_RIGHT`, `SLOW_FORWARD`, `SEEK_LIGHT_LEFT`, `SEEK_LIGHT_RIGHT`, `STOP`

**Training setup**:

- 200 episodes x 1,500 frames
- epsilon-greedy exploration (`1.0 -> 0.05`)
- `alpha=0.1`, `gamma=0.95`
- reward: `+10` per dirt collected, `-0.1` per frame, `-20` once per battery depletion

Hard cat-freeze and overlap overrides remain in place, so the learned policy only governs normal movement decisions.

## 3. Experimental Design

### 3.1 Standard Comparison

- 3 robots, 4 cats, 2 chargers, 1,500 frames per run
- 3 brain types x 10 random seeds
- metrics: dirt collected, collection rate, cat freeze events, battery depletion events

### 3.2 Cat Count Gradient

- cat count varies across `0, 2, 4, 6, 8`
- 3 brain types x 5 cat counts x 10 seeds
- purpose: robustness under increasing obstacle pressure

### 3.3 Training Duration

- Q-Learning retrained for `25, 50, 100, 150, 200` episodes
- each trained policy evaluated on 10 seeds
- purpose: how much training is actually useful

### 3.4 Generalization

- Q-Learning trained once in the standard environment, then evaluated without retraining
- four test configurations: `standard`, `single_bot`, `many_bots`, `hard_mode`
- purpose: transfer to unseen robot-count / obstacle-count settings

## 4. Results

### 4.1 Standard Comparison

![Cleaning Performance Comparison](rq1-figures/bar_dirt_collected.png)

| Algorithm | Mean Dirt | Std | Collection Rate | Cat Freezes | Battery Depletions |
|-----------|-----------|-----|-----------------|-------------|--------------------|
| Subsumption | 70.8 | ±14.4 | 0.047 | 0.0 | 0.0 |
| Potential Field | 64.4 | ±10.1 | 0.043 | 1.0 | 0.2 |
| **Q-Learning** | **85.3** | ±13.9 | **0.057** | 0.4 | 0.1 |

**Significance**:

- Q-Learning beats Subsumption on dirt collected (`p = 0.0342`)
- Q-Learning beats Potential Field on dirt collected (`p = 0.0012`)
- Subsumption has significantly fewer cat freezes than Potential Field (`p = 0.0011`) and Q-Learning (`p = 0.0248`)

![Collection Rate Distribution](rq1-figures/box_collection_rate.png)

The refreshed comparison now supports a stronger result than the stale report: **Q-Learning is the clear best performer in the standard environment**, not just a noisy near-tie.

### 4.2 Cat Count Gradient

![Impact of Cat Count on Cleaning Performance](rq1-figures/line_cat_gradient.png)

Mean dirt collected by cat count:

| Cat Count | Subsumption | Potential Field | Q-Learning |
|-----------|-------------|-----------------|------------|
| 0 | 90.2 | 73.9 | **90.4** |
| 2 | 86.5 | 69.2 | **91.5** |
| 4 | 70.8 | 64.4 | **85.3** |
| 6 | 66.1 | 56.7 | **77.3** |
| 8 | 56.6 | 58.1 | **68.9** |

Key observations:

- **Q-Learning remains the strongest controller across the full cat gradient**
- **Subsumption** degrades steadily as obstacle pressure increases
- **Potential Field** remains the weakest option in most settings, although at 8 cats it slightly exceeds Subsumption

### 4.3 Training Duration

![Effect of Training Duration](rq1-figures/line_training_duration.png)

| Training Episodes | Mean Dirt |
|-------------------|-----------|
| 25 | 68.7 |
| 50 | 75.0 |
| 100 | 82.8 |
| 150 | 66.1 |
| **200** | **85.3** |

The curve remains **non-monotonic**, but the best current result is now the full `200`-episode run. Longer training can still fail to help when the learning process drifts into weaker policies, yet the refreshed canonical model shows that the best observed policy in this setup comes from the longest run tested.

### 4.4 Generalization

| Environment | Subsumption | Potential Field | Q-Learning |
|-------------|-------------|-----------------|------------|
| Standard (3 bots, 4 cats) | 70.8 | 64.4 | **85.3** |
| Single bot (1 bot, 4 cats) | 29.2 | 25.2 | **38.7** |
| Many bots (5 bots, 4 cats) | 90.2 | 89.1 | **111.4** |
| Hard mode (1 bot, 8 cats) | 21.7 | 21.9 | **28.4** |

Q-Learning achieves the highest mean score in every evaluation environment. The margin is largest in the standard, single-bot, and many-bot settings, and remains meaningful even in the hardest configuration.

### 4.5 Safety Analysis

![Cat Encounter Safety](rq1-figures/bar_cat_freezes.png)

- **Subsumption** remains the safest policy: zero cat freezes and zero battery depletions in the standard comparison
- **Potential Field** shows the weakest safety profile: mean `1.0` cat freezes
- **Q-Learning** is still relatively safe, but not perfect: mean `0.4` cat freezes and `0.1` battery depletions

### 4.6 Training Curve

![Q-Learning Training Curve](rq1-figures/training_curve_reward.png)

The reward curve trends upward overall but remains noisy. This matches the training-duration study: learning is real, but policy quality is still sensitive to stochastic rollout variance.

### 4.7 Multi-Metric Overview

![Radar Comparison](rq1-figures/radar_comparison.png)

## 5. Discussion

### 5.1 Answering the Research Question

With the repaired controller logic, retrained Q-table, and refreshed analysis pipeline, the answer is now clearer:

- **Q-Learning is the best overall architecture** in this simulator when the main objective is dirt collection.
- **Subsumption** remains the strongest safety baseline and the easiest controller to reason about.
- **Potential Field** is consistently outperformed by Q-Learning and usually by Subsumption as well.

### 5.2 Key Findings

1. **Q-Learning now wins the standard comparison by a statistically significant margin** over both hand-designed baselines.
2. **Subsumption remains the safety baseline**, with zero freezes and zero depletions in the standard setup.
3. **APF is still the weakest of the three under current weights**, combining lower cleaning output with more freeze events.
4. **Q-Learning training is still unstable**, because intermediate training durations do not improve monotonically.

### 5.3 Limitations

- The tabular state representation is still coarse and may hide important geometry and temporal context.
- Q-Learning performance remains sensitive to stochastic training variance.
- Only one reward design is evaluated here; stronger safety penalties or curriculum training could change the ranking.
- The simulator remains a simplified 2D toroidal world rather than a full physical robot environment.

### 5.4 Future Work

- Tune APF weights systematically instead of hand-setting them once
- Improve Q-Learning reward shaping for energy management and stability
- Test curriculum learning or domain randomization across cat counts and robot counts
- Explore hybrid controllers that combine Subsumption-style safety layers with learned movement policies

## 6. Conclusion

After repairing the simulator logic and regenerating all RQ1 experiment outputs, **Q-Learning is the best-performing architecture overall** and now has statistically supported gains in the standard comparison. **Subsumption** remains the safest and most predictable controller. **Potential Field** is the least convincing option in the current implementation. The main follow-up question is no longer whether learning can beat hand-written rules here, but how to retain Q-Learning's performance advantage while tightening its safety guarantees and reducing training variance.
