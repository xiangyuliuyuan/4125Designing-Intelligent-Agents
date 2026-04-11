# Research Question 3: Sensor Noise Robustness

> **Question**: How sensitive is each agent architecture to sensor noise, and which architecture degrades most gracefully?

---

## 1. Background

Real-world sensors produce noisy readings due to calibration drift, environmental interference, and measurement uncertainty. This study injects multiplicative Gaussian noise into all sensor channels to measure how each agent architecture performs under imperfect perception. The noise model applies `signal *= max(0, 1 + N(0, sigma))` to every sensor reading, affecting light, debris, bot, cat, and charger detection equally.

## 2. Experimental Design

- **Noise levels (sigma)**: 0.0 (baseline), 0.1, 0.2, 0.3, 0.5, 1.0
- **Brain types**: Subsumption, Potential Field, Q-Learning
- **Configuration**: 3 robots, 4 cats, 2 chargers, 1500 frames
- **Repetitions**: 10 random seeds per condition
- **Total runs**: 6 x 3 x 10 = 180

The noise is applied at the lowest level — inside `calculate_sensor_values()` — so all sensors are affected consistently.

## 3. Results

### 3.1 Cleaning Performance Under Noise

![Noise Degradation](rq3-figures/line_noise_degradation.png)

| Sigma | Subsumption | Potential Field | Q-Learning |
|-------|-------------|-----------------|------------|
| 0.0 | 75.3 | 69.1 | **79.8** |
| 0.1 | **81.8** | 67.8 | 81.5 |
| 0.2 | 68.8 | 65.5 | **84.5** |
| 0.3 | 72.3 | 65.8 | **79.7** |
| 0.5 | 67.1 | 65.0 | **79.0** |
| 1.0 | 69.1 | 66.0 | **70.1** |

All three architectures show **surprising resilience** in cleaning performance. None of the dirt-collected changes are statistically significant at any noise level (all p > 0.2). Some conditions even show slight increases (e.g., Q-Learning at sigma=0.2 scores 84.5 vs baseline 79.8), but these are within random variance and not meaningful improvements. Q-Learning maintains the highest scores up to sigma=0.5, only dropping meaningfully at sigma=1.0.

### 3.2 Performance Retention

![Relative Performance](rq3-figures/bar_noise_relative.png)

At sigma=1.0, performance retention is:
- **Subsumption**: 91.8% of baseline
- **Potential Field**: 95.5% of baseline
- **Q-Learning**: 87.8% of baseline

Potential Field shows the most stable cleaning output, likely because its gradient-based force computation naturally smooths noisy inputs through the turn-smoothing filter.

### 3.3 Safety Under Noise

![Safety Under Noise](rq3-figures/line_noise_safety.png)

The **critical finding** is in safety, not cleaning:

| Sigma | Subsumption Freezes | APF Freezes | Q-Learning Freezes |
|-------|--------------------|--------------|--------------------|
| 0.0 | 0.0 | 1.8 | 0.5 |
| 0.1 | 0.2 | 3.1 | 0.6 |
| 0.2 | 0.4 | **7.6** (p=0.001) | 0.8 |
| 0.3 | 0.2 | 3.4 | **1.7** (p=0.008) |
| 0.5 | 1.3 | **15.2** (p<0.001) | **3.3** (p=0.002) |
| 1.0 | **6.4** (p<0.001) | **36.6** (p<0.001) | **9.8** (p<0.001) |

Statistical significance tests (vs sigma=0 baseline) confirm:

- **Potential Field** is by far the most noise-sensitive for safety: cat freezes become significantly elevated from sigma=0.2 onward (p=0.001), reaching 36.6 at sigma=1.0. Noisy cat signals cause the soft avoidance forces to miscalculate, leading to close cat encounters. The non-monotonic dip at sigma=0.3 (3.4, not significant) is likely sampling variance with n=10.
- **Q-Learning** shows significant safety degradation from sigma=0.3 onward (p=0.008), reaching 9.8 freezes at sigma=1.0.
- **Subsumption** stays safest up to sigma=0.5 (all p>0.15), only becoming significant at sigma=1.0 (p<0.001, 6.4 freezes). Its hard thresholds provide a partial shield against moderate noise.

## 4. Discussion

### 4.1 Key Findings

1. **Cleaning performance is surprisingly robust to noise** across all architectures — even sigma=1.0 (where sensor readings can double or zero out) only causes a ~10% drop.
2. **Safety is the true vulnerability**: noise primarily affects cat avoidance, not dirt collection. This makes sense — cats require precise distance estimation while dirt collection is more forgiving.
3. **Potential Field is the worst under noise** for safety, because its continuous force computation amplifies noise directly into steering. Threshold-based systems (Subsumption) at least have a clear "react or don't" boundary.
4. **Q-Learning shows moderate robustness** despite being trained without noise, suggesting the discretized state representation acts as a natural noise filter (continuous sensor values map to categorical buckets).

### 4.2 Limitations

- Only multiplicative noise tested; systematic bias or sensor dropout would behave differently.
- Q-Learning was trained without noise; retraining with noise could improve its robustness.
- The physical cat-freeze override (distance < 90px) is independent of sensors and provides a safety floor that limits how bad any architecture can perform.

## 5. Conclusion

Sensor noise affects **safety far more than cleaning efficiency**. Potential Field is the most noise-sensitive architecture due to its continuous force computation. Subsumption's hard thresholds provide a partial shield, and Q-Learning's state discretization acts as an implicit noise filter. For deployment in noisy environments, a hybrid approach using threshold-based safety with learned movement would be advisable.
