# Research Question 4: Reward Function Design

> **Question**: How do different reward function designs affect Q-Learning cleaning performance, training stability, and safety?

---

## 1. Background

RQ1 showed that Q-Learning performance depends heavily on training quality. This study tests whether the reward design is a major cause by training the same tabular Q-Learning agent with five reward variants and comparing both the learned policy quality and the training dynamics.

## 2. Reward Variants

| Variant | Reward Components |
|---------|-------------------|
| **Baseline** | +10 per dirt, -0.1 per frame, -20 per battery depletion |
| **Heavy Safety** | Baseline + (-5.0 per frame near cat, -20 per freeze) |
| **Dense Progress** | Baseline + (+2.0) when approaching light sources |
| **Energy Aware** | Baseline + (+5.0 when actively charging, -3.0 per frame when battery < 300) |
| **Sparse** | +10 per dirt only |

Each variant was trained independently for 200 episodes before evaluation.

## 3. Experimental Design

- **Training**: 200 episodes x 1500 frames, 3 bots, 4 cats, 2 chargers
- **Evaluation**: each trained Q-table tested on 10 random seeds (1500 frames)
- **Reference baseline**: Subsumption evaluated on the same seeds
- **Metrics**: dirt collected, cat freezes, battery depletions, training-curve shape

## 4. Results

### 4.1 Evaluation Performance

![Reward Comparison](rq4-figures/bar_reward_comparison.png)

| Variant | Mean Dirt | Std | Cat Freezes | Battery Depletions |
|---------|-----------|-----|-------------|-------------------|
| Subsumption (ref) | 70.8 | 14.4 | 0.0 | 0.0 |
| **Baseline** | **85.3** | 13.9 | 0.4 | 0.1 |
| Heavy Safety | 84.5 | 15.5 | 0.5 | 0.0 |
| Dense Progress | 78.3 | 12.8 | 0.3 | 0.1 |
| Energy Aware | 42.6 | 11.8 | 0.3 | 0.0 |
| Sparse | 81.1 | 13.8 | 0.2 | 0.0 |

The main statistical result is unchanged in direction but stronger in magnitude: **Energy Aware is catastrophically worse than Baseline** (`p < 0.0001`). The other reward variants are **not significantly different from Baseline**:

- Baseline vs Heavy Safety: `p = 0.9045`
- Baseline vs Dense Progress: `p = 0.2564`
- Baseline vs Sparse: `p = 0.5054`

### 4.2 Training Curves

![Training Curves](rq4-figures/line_reward_training.png)

The refreshed training curves support three broad patterns:

- **Baseline** and **Heavy Safety** both learn strong policies and finish near the top
- **Dense Progress** remains viable but underperforms the best two in final evaluation
- **Energy Aware** learns a much weaker policy, consistent with its low final mean

This indicates that reward shaping can matter, but only some shaping terms are useful in this coarse state space.

### 4.3 Performance Stability

![Stability Comparison](rq4-figures/box_reward_stability.png)

The stability plot shows two different kinds of behaviour:

- **Energy Aware** is relatively consistent, but consistently bad
- **Baseline**, **Heavy Safety**, and **Sparse** all occupy the strong-performance band with overlapping spread

So the key distinction is not variance alone, but whether the reward pushes the policy toward the right objective.

### 4.4 Safety

![Safety Comparison](rq4-figures/bar_reward_safety.png)

Safety differences between the strong variants are modest:

- Baseline: `0.4` freezes, `0.1` depletions
- Heavy Safety: `0.5` freezes, `0.0` depletions
- Dense Progress: `0.3` freezes, `0.1` depletions
- Sparse: `0.2` freezes, `0.0` depletions

The most important conclusion is that **extra safety-oriented reward terms do not produce a dramatic safety advantage**. The hard safety overrides in the controller still do most of the work.

## 5. Discussion

### 5.1 Key Findings

1. **Over-penalising low battery is highly damaging**. Energy Aware drops to `42.6` mean dirt, roughly half the Baseline score.
2. **Baseline remains the best-performing reward design** in the refreshed evaluation.
3. **Heavy Safety and Sparse are both competitive alternatives**, but neither beats Baseline significantly.
4. **Dense Progress is no longer the best variant** under the current code and retraining setup.
5. **Reward shaping has limited leverage compared with representation quality**: four variants cluster together while one bad penalty design collapses performance.

### 5.2 Why Energy Aware Fails

The `-3.0` per-frame penalty at very low battery is too strong relative to the main cleaning reward. It creates an incentive landscape where avoiding critical battery states matters more than collecting dirt. The learned policy becomes over-cautious and spends too much time prioritising charging-related behaviour.

### 5.3 Limitations

- Each reward variant is trained once; multiple independent training runs would give a more stable estimate.
- The tabular state representation is still coarse, which limits how much reward shaping can differentiate good policies.
- Hard-coded safety overrides bypass some dangerous situations before Q-Learning decisions are applied.

## 6. Conclusion

Reward design matters, but **bad shaping hurts more than clever shaping helps** in this project. The refreshed experiments show that **Baseline remains the strongest reward function**, while **Energy Aware is a clear failure mode**. Heavy Safety, Dense Progress, and Sparse all produce workable policies, but none improves enough over Baseline to justify replacing it. The more important bottleneck now appears to be the **state representation and training variance**, not the absence of sophisticated reward terms.
