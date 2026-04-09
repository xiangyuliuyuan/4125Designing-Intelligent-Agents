# COMP4125 Coursework - 机器人吸尘器仿真

基于 COMP4125 实践课提供的机器人吸尘器代码，扩展为多机器人自主智能体仿真系统。多个机器人在 2D 环绕边界（toroidal）环境中自主运行，执行清洁任务，同时管理电量、规避障碍物和猫、与其他机器人协调。

## 快速开始

```bash
# 需要 Python 3.9+（GUI 依赖 tkinter）

# 安装依赖
pip install -r requirements.txt

# 启动 GUI 仿真(⭐️)
python main.py

# 无 GUI 模式运行（用于自动化实验）
# python run_headless.py --seed 42 --frames 3000

# 运行测试
# python -m unittest -v
```

> **注意**：本项目核心仅依赖 Python 标准库（`tkinter`、`math`、`logging` 等），无需额外第三方库即可运行仿真。`requirements.txt` 中列出的是实验阶段用于数据分析和可视化的依赖。

## 项目结构

```
main.py                  # 程序入口
run_headless.py          # 无 GUI 模式，用于自动化实验
app/
  bootstrap.py           # 应用装配（UI + 仿真连接）
  context.py             # 初始仿真状态创建
  logging_config.py      # 双通道日志（文件 + 控制台）
simulation/
  astar.py               # A* 寻路算法
  counting.py            # 垃圾收集计数器
  engine.py              # 主仿真循环、暂停、重置
  factory.py             # 实体创建 / 删除 / 重置
  runtime.py             # 仿真运行时全局状态
  state.py               # 状态对象定义
  stats.py               # 统计数据计算
  passive_index.py       # 被动对象空间索引
robot/
  bot.py                 # 机器人实体（编排各子系统）
  brain.py               # 决策逻辑（subsumption 架构）
  sensing.py             # 传感器计算（灯光、机器人、杂物、猫、充电站）
  motion.py              # 差速驱动运动学 & 边界环绕
  cleaning.py            # 垃圾收集逻辑
  state_view.py          # 模式推导（用于日志）
entities/
  cat.py                 # 猫实体（带 panic-jump 行为的障碍物）
  charger.py             # 充电站实体
  dirt.py                # 垃圾 / 碎片实体（多种类型）
  lamp.py                # 灯实体（光源）
ui/
  window.py              # 画布初始化
  renderer.py            # 集中实体渲染
  controls.py            # 速度滑块、日志级别下拉框
  control_panel.py       # 增删实体按钮面板
  stats_panel.py         # 统计显示面板
  theme.py               # 颜色 / 样式常量
  tooltip.py             # 工具提示组件
tests/
  test_regressions.py    # 61 个回归测试
docs/
  CHANGES.md                 # 变更记录总览
  architecture-overview.md   # 模块架构说明
  bugfixes.md                # Bug 修复记录
  new-features.md            # 新增功能说明
```

## 使用的 AI 技术

### 1. Subsumption 架构（机器人决策）

机器人大脑（`robot/brain.py`）实现了基于优先级的 subsumption（包容式）架构，高优先级行为会抑制低优先级行为：

| 优先级 | 行为 | 触发条件 |
|--------|------|----------|
| 1（最高） | 重叠分离 | 机器人间信号 > 20000 |
| 2 | 低电量充电 | 电量 < 600，使用 A* 导航 |
| 3 | 猫冻结（紧急停车） | 猫信号 > 3000 |
| 4 | 猫回避（转向躲避） | 猫信号 > 700 |
| 5 | 碎片回避 | 碎片信号 > 5000 |
| 6 | 机器人回避 | 机器人信号 > 3000 |
| 7（最低） | 随机漫游 | 默认探索行为 |

### 2. A* 寻路算法（充电导航）

当电量低于阈值时，机器人使用 A* 搜索（`simulation/astar.py`）规划前往最近可用充电站的路径：
- 基于网格的世界寻路
- 障碍物分类（大块碎片不可通行，小垃圾可穿越）
- 路径被阻断或发现更优充电站时动态重规划
- 多充电站评估，考虑竞争者数量

### 3. 反应式猫回避（双边策略）

机器人与猫之间的双向回避系统：
- **机器人侧**：近距离传感器检测猫，大脑控制转向躲避
- **猫侧**：可配置距离内触发 panic-jump（惊跳远离）
- **引擎层安全网**：基于物理距离的冻结机制，即使传感器盲区也能防止碰撞

## 相对原始代码的主要改进

本项目基于课堂提供的单文件机器人仿真进行扩展，主要改动：

- **模块化架构**：从约 1200 行的单体文件重构为 31 个职责明确的模块
- **25 项 Bug 修复**：涵盖 A* 寻路、充电系统、运动物理、实体管理
- **9 项设计改进**：消除重复代码、死代码和不一致性
- **3 项新功能**：结构化日志系统、运行时日志级别 UI 控件、机器人主动避猫
- **61 个回归测试**：覆盖所有已修复 Bug 和新功能
- **Headless 模式**：`run_headless.py` 支持无 GUI 自动化实验

详细变更记录：
- [docs/CHANGES.md](docs/CHANGES.md) — 变更记录总览
- [docs/bugfixes.md](docs/bugfixes.md) — 所有 Bug 修复及根因分析
- [docs/architecture-overview.md](docs/architecture-overview.md) — 模块结构说明
- [docs/new-features.md](docs/new-features.md) — 新增功能文档

## Headless 实验模式

`run_headless.py` 在无 GUI 环境下运行仿真，用于自动化数据收集：

```bash
# 基本运行
python run_headless.py --seed 42 --frames 3000

# 自定义参数
python run_headless.py --seed 123 --frames 5000 --dt 1.0

# 输出包含碰撞次数、猫惊跳次数、冻结事件次数
```

Headless 模式使用 `FakeCanvas` 替代真实 Tk 画布，结构化事件日志输出到 `logs/headless.log`，便于事后分析 agent 行为。

## 默认仿真参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| 机器人数量 | 3 | 自主清洁机器人 |
| 猫数量 | 4 | 移动障碍物 |
| 充电站数量 | 2 | 充电设施 |
| 灯数量 | 2 | 光源 |
| 世界尺寸 | 1000 x 1000 | 环绕边界（toroidal） |
| 电池容量 | 1000 | 满电值 |
| 低电量阈值 | 600 | 触发充电行为 |
| 垃圾模式 | plus（多类型） | 包含多种垃圾类型，属性各异 |

## 日志系统

双通道结构化日志：

- **文件日志**（`logs/simulation.log`）：INFO 及以上级别，结构化键值对格式
- **控制台**：仅 WARNING 及以上
- **运行时控制**：两个通道的级别可通过 UI 下拉框独立调整，无需重启

日志格式示例：
```
tick=142 event=charging_started bot=Bot-1 charger=Charger-2 battery=587
tick=300 event=collision_detected bot=Bot-2 cat=Cat-1 distance=28.5
```

## 作业完成状态

### 已完成

- [x] 仿真环境搭建（2D toroidal 世界，多种实体）
- [x] 自主智能 Agent（多机器人，subsumption 决策架构）
- [x] AI 技术实现（A* 寻路 + subsumption 行为分层 + 反应式避猫）
- [x] 代码模块化重构与 Bug 修复
- [x] 回归测试（61 个）
- [x] Headless 实验模式基础设施
- [x] 结构化日志系统

### 待完成

- [ ] **提出 5+ 研究问题**（每人负责一个问题及对应实验）
- [ ] **实验脚本编写**（基于 `run_headless.py` 扩展，变化参数、多次运行、收集数据）
- [ ] **数据分析与可视化**（图表、描述性统计、推断性统计）
- [ ] **撰写报告**（4000-8000 字，含文献综述、实验设计、结果分析、反思总结、成员分工）
- [ ] **准备 Presentation**（15 分钟小组演示）

### 建议的研究问题方向

以下问题可直接基于现有代码扩展实验：

1. **机器人数量 vs 清洁效率**：改变机器人数量（1-6），观察单位时间垃圾收集量、碰撞频率、资源竞争情况
2. **A* 寻路 vs 随机漫步充电**：对比有/无 A* 导航时的充电成功率、电量耗尽次数、平均电量
3. **猫数量对机器人性能的影响**：改变猫数量（0-8），分析碰撞率、清洁效率下降程度、避猫行为频率
4. **不同感知/避让策略的比较**：对比纯反应式 vs subsumption 架构下的任务完成率
5. **充电站数量与布局对能源管理的影响**：改变充电站数量，观察电量耗尽事件和充电等待时间
