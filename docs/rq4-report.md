# Research Question 4: Reward Function Design

> **Question**: How do different reward function designs affect Q-Learning cleaning performance, training stability, and safety?

---

## 1. Background

RQ1 revealed that Q-Learning's training curve is non-monotonic: more training episodes do not reliably improve performance. This study investigates whether the reward function design is responsible, by training the same Q-Learning agent with five different reward signals and comparing both the training dynamics and the resulting policy quality.

## 2. Reward Variants

| Variant | Reward Components |
|---------|-------------------|
| **Baseline** | +10 per dirt, -0.1 per frame, -20 per battery depletion |
| **Heavy Safety** | Baseline + (-5.0 per frame near cat, -20 per freeze) |
| **Dense Progress** | Baseline + (+2.0) when approaching light sources (dirt) |
| **Energy Aware** | Baseline + (+5.0 when actively charging, -3.0 per frame when battery < 300) |
| **Sparse** | +10 per dirt only (no frame penalty, no battery penalty) |

Each variant was trained with a different random seed to ensure independent training trajectories.

## 3. Experimental Design

- **Training**: 200 episodes x 1500 frames, 3 bots, 4 cats, 2 chargers, different base seed per variant
- **Evaluation**: each trained Q-table tested on 10 random seeds (1500 frames)
- **Baseline comparison**: Subsumption architecture evaluated on same seeds
- **Metrics**: dirt collected, cat freezes, battery depletions, training curve shape

## 4. Results

### 4.1 Evaluation Performance

![Reward Comparison](rq4-figures/bar_reward_comparison.png)

| Variant | Mean Dirt | Std | Cat Freezes | Battery Depletions |
|---------|-----------|-----|-------------|-------------------|
| Subsumption (ref) | 75.3 | 14.4 | 0.0 | 0.0 |
| Baseline | **79.8** | 18.7 | 0.5 | 0.1 |
| Heavy Safety | 78.3 | 16.3 | 0.3 | 0.3 |
| Dense Progress | **80.0** | 15.5 | 0.4 | 0.0 |
| Energy Aware | 52.8 | 9.5 | 0.3 | 0.1 |
| Sparse | 79.2 | 12.2 | 0.5 | 0.1 |

**Key result**: Energy Aware is **significantly worse** than Baseline (p=0.0007), while all other Q-Learning variants are statistically indistinguishable from Baseline (p > 0.85). The continuous low-battery penalty causes the agent to learn an overly cautious policy that prioritizes charging over cleaning.

### 4.2 Training Curves

![Training Curves](rq4-figures/line_reward_training.png)

The training curves reveal different learning dynamics:

- **Dense Progress** shows the most volatile training but achieves the highest mean (80.0), suggesting that the light-approach bonus provides useful gradient information.
- **Heavy Safety** produces a slightly more conservative policy (78.3) as the continuous cat-proximity penalty discourages exploration near cats.
- **Energy Aware** training produces consistently lower rewards because the agent over-invests in charging behavior, leaving less time for cleaning.
- **Sparse** and **Baseline** are nearly interchangeable, confirming that the frame penalty (-0.1) has minimal impact.

### 4.3 Performance Stability

![Stability Comparison](rq4-figures/box_reward_stability.png)

The boxplot reveals that **Energy Aware** has the tightest variance (std=9.5) but also the lowest mean (52.8) -- it has learned a consistent but suboptimal policy. **Sparse** shows the second-tightest variance (std=12.2) with competitive mean (79.2), making it the most reliably good variant.

### 4.4 Safety

![Safety Comparison](rq4-figures/bar_reward_safety.png)

Heavy Safety and Energy Aware tie for the lowest cat freeze rate (0.3 each) compared to Baseline (0.5), but the improvement is modest and statistically insignificant. Dense Progress achieves 0.0 battery depletions, the best energy management among Q-Learning variants.

## 5. Discussion

### 5.1 Key Findings

1. **Reward shaping can dramatically hurt performance**: the Energy Aware variant's continuous penalty for low battery (mean=52.8) performs 34% worse than Baseline (mean=79.8, p=0.0007). Over-penalizing a secondary objective causes the agent to neglect its primary task.

2. **Most reward variants converge to similar performance**: Baseline, Heavy Safety, Dense Progress, and Sparse all score 78-80 dirt, suggesting the coarse state space limits how much reward design can differentiate policies.

3. **Dense Progress is the best overall**: it matches Baseline in mean (80.0) with lower variance (std=15.5 vs 18.7) and achieves zero battery depletions, making it the most balanced variant.

4. **Sparse reward is surprisingly strong**: removing the frame penalty and battery penalty entirely (Sparse, mean=79.2) has no significant effect, confirming that the +10 dirt reward dominates the learning signal.

5. **Safety-oriented rewards have limited impact**: the Heavy Safety cat-proximity penalty reduces freezes from 0.5 to 0.3, but the hard-coded safety overrides in the Q-Learning brain already handle most cat encounters before the learned policy is consulted.

### 5.2 Why Energy Aware Failed

The Energy Aware variant's -3.0 per frame at critical battery creates a strong negative signal that dominates the reward landscape. The agent learns to prioritize charging above all else, spending excessive time near chargers. This demonstrates a classic reward design pitfall: **penalty magnitude must be calibrated relative to the primary reward signal**. A -3.0 per frame penalty accumulates faster than the +10 per dirt bonus can offset it.

### 5.3 Limitations

- Only one state representation tested; finer discretization could amplify reward differences.
- Fixed hyperparameters (alpha, gamma, epsilon schedule) across all variants.
- Safety overrides bypass Q-learning, limiting how much safety-oriented rewards can teach.
- Each variant trained only once (200 episodes); multiple independent training runs would provide more robust Q-tables.

## 6. Conclusion

Reward function design can significantly affect Q-Learning policy quality, but the direction of effect is not always intuitive. **Over-penalizing secondary objectives (like energy management) can catastrophically degrade primary task performance**. Among the variants tested, **Dense Progress** offers the best balance of cleaning efficiency, low variance, and energy management. **Sparse** reward is surprisingly competitive, suggesting that in environments with a clear primary objective, minimal reward signals may be preferable to complex multi-objective designs. The main bottleneck remains the coarse state representation, which limits how much any reward signal can differentiate learned policies.
