# Research Question 3: Sensor Noise Robustness

> **Question**: How sensitive is each agent architecture to sensor noise, and which architecture degrades most gracefully?

---

## 1. Background

Real-world sensors produce noisy readings due to calibration drift, environmental interference, and measurement uncertainty. This study injects multiplicative Gaussian noise into all sensor channels to measure how each architecture performs under imperfect perception. The noise model applies `signal *= max(0, 1 + N(0, sigma))` to every sensor reading, affecting light, debris, bot, cat, and charger detection equally.

## 2. Experimental Design

- **Noise levels (sigma)**: 0.0 (baseline), 0.1, 0.2, 0.3, 0.5, 1.0
- **Brain types**: Subsumption, Potential Field, Q-Learning
- **Configuration**: 3 robots, 4 cats, 2 chargers, 1500 frames
- **Repetitions**: 10 random seeds per condition
- **Total runs**: 6 x 3 x 10 = 180

The noise is applied inside `calculate_sensor_values()`, so all sensing channels are perturbed consistently.

## 3. Results

### 3.1 Cleaning Performance Under Noise

![Noise Degradation](rq3-figures/line_noise_degradation.png)

| Sigma | Subsumption | Potential Field | Q-Learning |
|-------|-------------|-----------------|------------|
| 0.0 | 70.8 | 64.4 | **85.3** |
| 0.1 | 69.5 | 67.2 | **86.3** |
| 0.2 | 68.6 | 59.2 | **84.2** |
| 0.3 | 71.7 | 63.1 | **83.2** |
| 0.5 | 68.1 | 62.1 | **83.6** |
| 1.0 | 65.0 | 66.3 | **77.7** |

None of the dirt-collected changes relative to `sigma = 0.0` are statistically significant for any architecture (`all p > 0.28`). The main result is therefore not “noise ruins cleaning”, but rather that **cleaning output is surprisingly robust even under very heavy multiplicative noise**.

### 3.2 Performance Retention

![Relative Performance](rq3-figures/bar_noise_relative.png)

At `sigma = 1.0`, performance retention relative to the noise-free baseline is:

- **Subsumption**: 91.8%
- **Potential Field**: 102.9%
- **Q-Learning**: 91.1%

Potential Field appears most stable on this narrow metric, but that is misleading on its own because its safety behaviour degrades much more sharply.

### 3.3 Safety Under Noise

![Safety Under Noise](rq3-figures/line_noise_safety.png)

The dominant effect of noise is on **cat-freeze frequency**, not on dirt collection:

| Sigma | Subsumption Freezes | APF Freezes | Q-Learning Freezes |
|-------|--------------------|-------------|--------------------|
| 0.0 | 0.0 | 1.0 | 0.4 |
| 0.1 | 0.4 | 3.0 | 0.7 |
| 0.2 | 0.9 | 5.9 | 0.6 |
| 0.3 | 1.4 | 4.3 | 1.4 |
| 0.5 | 2.9 | 15.0 | 2.2 |
| 1.0 | 13.3 | 34.5 | 10.8 |

Significance tests against the noise-free baseline show:

- **Subsumption** becomes significantly worse from `sigma = 0.2` onward
- **Potential Field** also becomes significantly worse from `sigma = 0.2` onward
- **Q-Learning** does not show a significant freeze increase until `sigma = 0.3`

At moderate noise levels (`0.2` to `0.5`), **Q-Learning is the most robust safety-wise**, while Potential Field is consistently the worst. At extreme noise (`sigma = 1.0`), every controller degrades sharply, but APF fails by far the hardest.

Battery depletion stays near zero across the entire study, so the robustness question is primarily about **collision avoidance quality**, not energy management.

## 4. Discussion

### 4.1 Key Findings

1. **Cleaning performance is robust to sensor noise** across all architectures in this simulator.
2. **Safety is the true vulnerability**: noisy cat perception causes freeze events to rise long before dirt collection collapses.
3. **Potential Field is the least noise-robust architecture overall**, because its continuous steering reacts directly to noisy gradients.
4. **Q-Learning is the strongest all-round option under noise**, keeping the highest cleaning score at every sigma and delaying significant safety degradation until `sigma = 0.3`.
5. **Subsumption remains competitive but not noise-immune**; once its thresholds are crossed incorrectly often enough, freeze events also rise substantially.

### 4.2 Limitations

- Only multiplicative Gaussian noise is tested; systematic bias or sensor dropout could produce different failure modes.
- Q-Learning is evaluated without noise-aware retraining; robustness could improve further with noisy training data.
- The simulator's hard physical freeze override still provides a safety floor, limiting worst-case behavioural divergence.

## 5. Conclusion

Sensor noise affects **safety much more than cleaning throughput** in this project. **Q-Learning** remains the best-performing controller across the full noise range and is also the most robust under moderate noise. **Potential Field** is the most noise-sensitive architecture, especially in safety-critical cat encounters. **Subsumption** offers a predictable baseline, but its threshold logic still degrades once noise becomes strong enough to flip decisions frequently.
