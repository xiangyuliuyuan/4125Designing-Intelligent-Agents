# Research Question 1: Three-Way Agent Architecture Comparison

> **Question**: How do three fundamentally different agent architectures — rule-based (Subsumption), reactive (Artificial Potential Field), and learning-based (Q-Learning) — compare in cleaning task performance, and what are their respective strengths and weaknesses?

This report has been refreshed after fixing the experiment pipeline so that:

- `cat_freeze_count` and `battery_depletions` are counted as transition events rather than per-frame occupancy
- Q-Learning applies its final episode reward before resetting
- analysis scripts parse the current Q-table JSON format and 7-action policy space

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
| 2 | Low-battery charging (A* navigation) | Battery < 600 |
| 3 | Cat freeze | Cat signal > 3,000 |
| 4 | Cat avoidance | Cat signal > 700 |
| 5 | Debris avoidance | Debris signal > 5,000 |
| 6 | Bot avoidance | Bot signal > 3,000 |
| 7 (lowest) | Random wandering | Default |

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
| Subsumption | 75.3 | ±14.4 | 0.050 | 0.0 | 0.0 |
| Potential Field | 69.1 | ±9.6 | 0.046 | 1.8 | 0.0 |
| **Q-Learning** | **79.8** | ±18.6 | **0.053** | 0.5 | 0.1 |

**Significance**:

- Dirt collected: no pairwise comparison is significant at `alpha = 0.05`
- Cat freezes: Subsumption vs Potential Field is significant (`p = 0.012`)

![Collection Rate Distribution](rq1-figures/box_collection_rate.png)

The refreshed comparison changes the earlier story: Q-Learning still has the highest average cleaning score, but the margin is small and noisy rather than overwhelming.

### 4.2 Cat Count Gradient

![Impact of Cat Count on Cleaning Performance](rq1-figures/line_cat_gradient.png)

Mean dirt collected by cat count:

| Cat Count | Subsumption | Potential Field | Q-Learning |
|-----------|-------------|-----------------|------------|
| 0 | 89.3 | 73.4 | **89.6** |
| 2 | 83.8 | 67.4 | **89.4** |
| 4 | 75.3 | 69.1 | **79.8** |
| 6 | 68.8 | 62.1 | **76.3** |
| 8 | 56.3 | 67.4 | **68.7** |

Key observations:

- **Subsumption** declines steadily as cats increase (`89.3 -> 56.3`)
- **Potential Field** remains inconsistent and never becomes the strongest option
- **Q-Learning** stays best across the full gradient and degrades more slowly than Subsumption

### 4.3 Training Duration

![Effect of Training Duration](rq1-figures/line_training_duration.png)

| Training Episodes | Mean Dirt |
|-------------------|-----------|
| 25 | 86.6 |
| 50 | 76.7 |
| **100** | **88.6** |
| 150 | 77.8 |
| 200 | 79.8 |

The curve is clearly **non-monotonic**. More training is not automatically better in the current setup. The best mean score appears at `100` episodes, while `25` episodes is already competitive. This suggests that the current reward design and data distribution produce a noisy learning process rather than smooth convergence.

### 4.4 Generalization

| Environment | Subsumption | Potential Field | Q-Learning |
|-------------|-------------|-----------------|------------|
| Standard (3 bots, 4 cats) | 75.3 | 69.1 | **79.8** |
| Single bot (1 bot, 4 cats) | 30.8 | 25.6 | **35.8** |
| Many bots (5 bots, 4 cats) | 95.7 | 89.5 | **102.2** |
| Hard mode (1 bot, 8 cats) | 23.6 | 23.5 | **27.5** |

Q-Learning achieves the highest mean score in every environment, but the advantage is moderate rather than dramatic. The strongest relative gap appears in the single-bot case.

### 4.5 Safety Analysis

![Cat Encounter Safety](rq1-figures/bar_cat_freezes.png)

- **Subsumption** remains the safest policy: zero cat freezes and zero battery depletions in the standard comparison
- **Potential Field** shows the weakest safety profile: mean `1.8` cat freezes
- **Q-Learning** is mostly safe but not perfect: mean `0.5` cat freezes and `0.1` battery depletions

### 4.6 Training Curve

![Q-Learning Training Curve](rq1-figures/training_curve_reward.png)

The reward curve trends upward overall, but with large episode-to-episode variance. This matches the non-monotonic training-duration study: learning is happening, but the policy quality is sensitive to training length and stochastic rollout variance.

### 4.7 Multi-Metric Overview

![Radar Comparison](rq1-figures/radar_comparison.png)

## 5. Discussion

### 5.1 Answering the Research Question

The repaired experiments support a more conservative answer than the original draft:

- **Subsumption** is still the strongest choice when safety and predictability matter most. Its cleaning score is close to Q-Learning in the standard setup while keeping perfect safety metrics.
- **Potential Field** is not a compelling middle ground under the current tuning. It underperforms Subsumption on both mean dirt and safety.
- **Q-Learning** delivers the best overall cleaning and the best transfer to unseen environments, but the gain is modest and comes with some residual safety and training-stability issues.

### 5.2 Key Findings

1. **Q-Learning still leads overall**, but the advantage is smaller than the stale report claimed.
2. **Subsumption remains the safety baseline** with zero freeze and zero depletion events in the standard comparison.
3. **APF is the weakest of the three under current weights**, showing both lower efficiency and higher freeze counts.
4. **Training stability is now the main Q-Learning weakness**: longer training does not reliably improve performance.

### 5.3 Limitations

- The tabular state representation is still coarse and may hide important geometry and temporal context.
- Q-Learning performance is sensitive to stochastic training variance.
- Only one reward design is evaluated here; stronger battery penalties or curriculum training could change the ranking.
- The simulator remains a simplified 2D toroidal world rather than a full physical robot environment.

### 5.4 Future Work

- Tune APF weights systematically instead of hand-setting them once
- Improve Q-Learning reward shaping for energy management and stability
- Test curriculum learning or domain randomization across cat counts and robot counts
- Explore hybrid controllers that combine Subsumption-style safety layers with learned movement policies

## 6. Conclusion

After repairing the experiment pipeline and regenerating all results, **Q-Learning remains the best-performing architecture overall**, especially in generalization, but it no longer dominates by a wide or statistically significant margin in the standard comparison. **Subsumption** remains the most reliable and safest controller. **Potential Field** is the least convincing option in the current implementation. The most important follow-up is no longer “prove Q-Learning wins”, but rather “make learned performance more stable without losing the safety guarantees of rule-based control.”
