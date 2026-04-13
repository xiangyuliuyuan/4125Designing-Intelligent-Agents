# Research Question 2: Robot Count Scaling

> **Question**: How does cleaning performance scale with the number of robots (1-10), and at what point do diminishing returns set in?

---

## 1. Background

Multi-robot systems face a fundamental trade-off: more robots can cover more area, but they also compete for resources such as chargers, light-adjacent dirt patches, and free movement space. This study measures how both total cleaning output and per-robot efficiency change as robot count increases from 1 to 10.

## 2. Experimental Design

- **Robot counts**: 1, 2, 3, 5, 7, 10
- **Brain types**: Subsumption, Potential Field, Q-Learning
- **Configuration**: 4 cats, 2 chargers, 1500 frames per run
- **Repetitions**: 10 random seeds per condition
- **Total runs**: 6 x 3 x 10 = 180
- **Metrics**: total dirt collected, dirt per robot, cat freeze events, battery depletions

## 3. Results

### 3.1 Total Cleaning Performance

![Total Dirt vs Robot Count](rq2-figures/line_scaling_total.png)

| Bots | Subsumption | Potential Field | Q-Learning |
|------|-------------|-----------------|------------|
| 1 | 29.2 | 25.2 | **38.7** |
| 2 | 51.0 | 52.4 | **67.4** |
| 3 | 70.8 | 64.4 | **85.3** |
| 5 | 90.2 | 89.1 | **111.4** |
| 7 | 116.1 | 98.1 | **131.3** |
| 10 | 118.7 | 109.5 | **129.4** |

All three architectures scale upward as robots are added, but the gains are clearly **sub-linear**. Adjacent-count t-tests show significant gains all the way from 1 to 7 robots for every architecture, while **7 to 10 robots is no longer significant** for any of them:

- Subsumption: `p = 0.7424`
- Potential Field: `p = 0.0652`
- Q-Learning: `p = 0.8103`

This places the main diminishing-returns breakpoint around **7 robots** in the current environment.

### 3.2 Per-Robot Efficiency

![Per-Robot Efficiency](rq2-figures/line_scaling_per_bot.png)

| Bots | Subsumption | Potential Field | Q-Learning |
|------|-------------|-----------------|------------|
| 1 | 29.2 | 25.2 | **38.7** |
| 2 | 25.5 | 26.2 | **33.7** |
| 3 | 23.6 | 21.5 | **28.4** |
| 5 | 18.0 | 17.8 | **22.3** |
| 7 | 16.6 | 14.0 | **18.8** |
| 10 | 11.9 | 11.0 | **12.9** |

Per-robot efficiency falls steadily for every controller. At 10 robots, each agent contributes only around one-third of the output of a single-robot run. Q-Learning remains the best architecture on this metric at every robot count, but even it cannot escape the same congestion trend.

### 3.3 Safety at Scale

![Safety Metrics](rq2-figures/bar_scaling_safety.png)

Cat freezes and battery depletions both rise with scale, but they do so in different patterns:

- **Subsumption** stays very safe through 7 robots, then jumps to `1.8` freezes and `4.2` battery depletions at 10 robots
- **Potential Field** accumulates the most cat freezes overall, peaking at `6.3` freezes at 7 robots
- **Q-Learning** stays comparatively safe through 5 robots and remains below Potential Field on freeze count at every scale

Battery depletion becomes the clearest shared bottleneck once the team size reaches 7-10 robots:

| Bots | Subsumption | Potential Field | Q-Learning |
|------|-------------|-----------------|------------|
| 5 | 0.3 | 0.6 | 0.2 |
| 7 | 1.2 | 1.4 | 1.2 |
| 10 | 4.2 | 3.9 | 3.8 |

## 4. Discussion

### 4.1 Key Findings

1. **Total output scales sub-linearly** for all three architectures.
2. **The practical scaling limit is around 7 robots** in this map with 2 chargers; adding robots beyond that yields little extra dirt.
3. **Q-Learning scales best overall**, keeping the highest total output and per-robot efficiency at every tested count.
4. **Charger contention becomes the main systems bottleneck** at large team sizes, visible in the sharp rise in battery depletions at 7 and 10 robots.
5. **Potential Field has the weakest safety profile under scale**, while Subsumption remains the most predictable until the highest crowding level.

### 4.2 Limitations

- Only one world size (`1000x1000`) is tested; a larger map could delay the onset of diminishing returns.
- Charger count is fixed at 2; scaling behaviour would likely improve with more charging resources.
- Q-Learning is trained in the standard 3-robot environment and then transferred to other team sizes without adaptation.

## 5. Conclusion

The system shows clear diminishing returns as robot count increases. In the current environment, **performance keeps improving up to 7 robots, but the jump from 7 to 10 is no longer statistically meaningful**. **Q-Learning** scales best on both total output and per-robot efficiency, while **Subsumption** remains the safest controller at moderate team sizes. The main practical lesson is that adding robots without adding chargers eventually stops helping.
