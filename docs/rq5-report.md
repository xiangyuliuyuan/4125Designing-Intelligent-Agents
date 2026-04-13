# Research Question 5: Memory-Augmented Navigation

> **Question**: Does giving the robot spatial memory (a visited-cell coverage map) improve cleaning efficiency over memoryless reactive control?

---

## 1. Background

The default Subsumption controller uses random wandering as its lowest-priority behaviour, with no explicit memory of where it has been. This means robots can revisit already-cleaned areas. To test whether simple spatial memory helps, this study implements a **Coverage Map Brain** that extends the Subsumption architecture with a 50x50 grid of visit counts. When no higher-priority behaviour is active, the robot steers toward the nearest least-visited cell instead of wandering randomly.

### 1.1 Coverage Brain Design

The `CoverageMapBrain` (`robot/brain_coverage.py`) keeps the same safety-first priority stack as Subsumption. Only the default exploration layer changes:

1. Discretize the 1000x1000 world into a 50x50 grid (20px cells)
2. Each frame, increment the visit counter for the bot's current cell
3. Find the nearest cell with the minimum visit count
4. Steer toward that target cell when no higher-priority behaviour is active

## 2. Experimental Design

- **Brain types**: Subsumption, Coverage, Q-Learning
- **Run durations**: Short (1500 frames) and Long (5000 frames)
- **Configuration**: 3 robots, 4 cats, 2 chargers
- **Repetitions**: 10 random seeds per condition
- **Additional metric**: final coverage percentage (fraction of grid cells visited at least once)

## 3. Results

### 3.1 Cleaning Performance

![Coverage Comparison](rq5-figures/bar_coverage_comparison.png)

| Brain | Short (1500f) | Long (5000f) |
|-------|---------------|--------------|
| Subsumption | 70.8 | 136.1 |
| Coverage | 57.9 | 93.3 |
| **Q-Learning** | **85.3** | **154.4** |

The Coverage brain collects **significantly less dirt than Subsumption** in both settings:

- short runs: `p = 0.0318`
- long runs: `p = 0.0005`

The deficit is substantial rather than marginal:

- short: Coverage is about **18% below** Subsumption
- long: Coverage is about **31% below** Subsumption

### 3.2 Coverage Over Time

![Coverage Over Time](rq5-figures/line_coverage_over_time.png)

| Brain | Short Coverage | Long Coverage |
|-------|----------------|---------------|
| Subsumption | 15.25% | 34.98% |
| Coverage | 13.84% | 25.37% |
| **Q-Learning** | **17.81%** | **37.56%** |

The central surprise survives the refresh: **the coverage brain covers less area despite explicitly trying to spread out**. In long runs it reaches only `25.37%` of the grid, versus `34.98%` for plain Subsumption and `37.56%` for Q-Learning.

### 3.3 Safety

![Safety Comparison](rq5-figures/bar_coverage_safety.png)

| Brain | Short Freezes | Long Freezes | Short Batt. Depl. | Long Batt. Depl. |
|-------|--------------|--------------|-------------------|------------------|
| Subsumption | 0.0 | 0.8 | 0.0 | 0.0 |
| Coverage | 0.1 | 0.7 | 0.0 | 0.0 |
| Q-Learning | 0.4 | 1.0 | 0.1 | 0.3 |

Coverage preserves the same general safety profile as Subsumption. The exploration-memory layer does not introduce a major safety regression, but it also does not deliver the intended exploration benefit.

## 4. Discussion

### 4.1 Why Coverage Does Not Help Here

The key result is that **simple visit-count memory is not the same thing as useful exploration**:

1. **Nearest least-visited targeting creates narrow, repeated routes** rather than broad exploration.
2. **The coverage map knows visits, not dirt density**. It can pull robots away from lamp-adjacent regions where dirt is more likely to appear.
3. **Subsumption's random wandering plus avoidance already creates decent spatial spread**, especially over long runs.
4. **Q-Learning outperforms both on coverage and cleaning**, suggesting that learned movement captures better implicit exploration than this hand-built memory heuristic.

### 4.2 Key Findings

1. **Spatial memory hurts cleaning efficiency** in this environment rather than helping it.
2. **Coverage brain also covers less area than the memoryless baseline**, so it fails on its own exploration objective.
3. **Safety stays close to Subsumption**, confirming that the safety stack still dominates risky situations.
4. **Q-Learning remains the strongest reference point**, beating both hand-designed controllers on cleaning and on final area coverage.

### 4.3 Limitations

- Only one coverage strategy is tested: nearest least-visited cell.
- The memory is per-robot rather than shared across the team.
- The map tracks visits only, not where dirt was found or where congestion occurs.
- The chosen grid resolution may not match the robot motion dynamics well.

## 5. Conclusion

Adding simple spatial memory through a visit-count coverage map **does not improve cleaning in this simulator**. It makes performance worse in both short and long runs, and it even reduces final area coverage relative to standard Subsumption. The result is not that memory is useless in principle, but that **this particular memory signal is poorly aligned with the task**. Future work should focus on **dirt-aware or team-shared memory**, not pure “go where I have visited least” exploration.
