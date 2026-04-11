# 变更记录总览

> 适用版本：v1.1

本文档记录在接手原始项目后所做的全部改动，供原项目团队参考。

## 2026-04-10 修复补充

本轮补充修复集中处理了回归审查中发现的三类问题：

- **仿真实体生成**：初始世界创建、`add bot` 和 `add cat` 现在都会避开现有机器人和猫，消除了启动即重叠和运行中即时重叠的问题
- **UI 行为一致性**：Brain 选择器与 `Reset` 语义保持一致；新增/删除实体会立即刷新统计面板；键盘快捷键会忽略已聚焦的控件；tooltip 会持续更新并优先显示最上层对象
- **实验与文档工件**：Q-Learning 终局奖励更新、实验事件计数、Q-table 解析/可视化和 RQ1 数据图表已整体修正并重新生成

## 改动分类

| 类别 | 数量 | 详细文档 |
|------|------|---------|
| Bug 修复（功能缺陷） | 25 项 | [bugfixes.md](bugfixes.md#功能性-bug) |
| 设计问题修复 | 9 项 | [bugfixes.md](bugfixes.md#设计问题) |
| 模块化重构 | 2 轮 | [architecture-overview.md](architecture-overview.md) |
| 新增功能 | 5 项 | [new-features.md](new-features.md) |
| 研究问题实验 | RQ1 | [new-features.md](new-features.md#5-研究问题-1替代决策架构与实验框架) |

---

## Bug 修复概览

共修复 25 个功能性缺陷，覆盖以下方向：

- **A* 路径规划**：障碍物判断错误、路径跟随代码被注释、垃圾类型误判、起点在障碍物上失败、边界越界、失败后不重试
- **充电系统**：充电模式提前退出、删除充电站后机器人持有悬挂引用、删除机器人后充电站锁死、远距离等待、等待期间耗电过快
- **机器人运动**：直线运动和猫移动均忽略时间步长 `dt`、零电量仍继续移动、越界坐标延迟一帧才修正
- **实体与感知**：灯光信号误触发机器人避让、基础垃圾类型无法收集
- **启动与 UI**：模块导入副作用、重置后暂停按钮状态不一致、`initialise()` 对 Frame 调用 `resizable()`

另修复 9 个设计问题，包括重复代码提取、冗余逻辑清理、猫跳走方向反向。

详见 → [bugfixes.md](bugfixes.md)

---

## 重构概览

分两轮完成，目标是将原单体 `main.py`（约 1200 行）拆分为职责明确的模块结构。

**重构前的主要问题：**
- `main.py` 同时承担入口、UI、仿真循环、实体定义、机器人行为等所有职责
- `Bot` 类聚合了传感、导航、移动、充电、清洁和绘制逻辑，单类职责过重
- 测试需要裁剪 `main.py` 才能加载模块

**重构后的模块结构：**

```
main.py              # 薄入口 + 兼容导出
app/                 # 应用装配（bootstrap、context、logging）
simulation/          # 仿真运行时（engine、state、factory、stats）
robot/               # 机器人行为（brain、sensing、motion、cleaning）
entities/            # 环境实体（cat、charger、dirt、lamp）
ui/                  # Tkinter 组件（window、renderer、controls、control_panel、stats_panel、theme、tooltip）
```

`counting.py` 和 `astar.py` 已移入 `simulation/` 包，根目录的 `cat.py`、`charger.py`、`dirt.py` 兼容包装层已移除，所有调用方已更新为从 `entities/` 和 `simulation/` 直接导入。

详见 → [architecture-overview.md](architecture-overview.md)

---

## 新增功能概览

| 功能 | 简述 |
|------|------|
| 结构化日志系统 | 将所有 `print()` 替换为双通道日志，`INFO` 写文件，`WARNING` 以上进控制台 |
| UI 日志级别控件 | 在运行参数区新增两个下拉框，可运行时独立调整文件/控制台日志级别 |
| 机器人主动避猫 | 机器人新增猫感知能力，猫提前进入 panic 跳离，降低接触概率 |
| 无头仿真模式 | `run_headless.py` 无 GUI 运行仿真，支持自动化实验和数据采集 |
| RQ1 替代决策架构与实验框架 | 新增 APF、Q-Learning 两种决策大脑和完整的训练/实验/分析流水线 |

详见 → [new-features.md](new-features.md)

---

## 研究问题 1 概览

为回答"不同智能体架构在清扫任务中的表现差异"，新增以下内容：

- **替代决策大脑**：人工势场法（`robot/brain_potential_field.py`）和 Q-Learning（`robot/brain_qlearning.py`），均与 Subsumption 接口兼容
- **无头仿真模式**：`run_headless.py` 无 GUI 运行，支持脚本驱动的批量实验
- **实验框架**：`experiments/` 包，提供 Q-Learning 训练、批量对比实验、泛化测试和统计分析/图表生成

实验结论（修复后重跑）：Q-Learning 在标准对比、猫梯度和泛化测试中都保持最高平均清扫量；Subsumption 安全性最高；APF 在当前参数下效率和安全性都不占优。

详见 → [new-features.md](new-features.md#5-研究问题-1替代决策架构与实验框架)、[rq1-report.md](rq1-report.md)

---

## 测试状态

当前全部 79 个回归测试通过（`python -m pytest tests/test_regressions.py -q` 与 `python3 -m unittest -q`）。
