# Refactored Architecture Overview

## 目标

本次重构将原本集中在 `main.py` 的入口、仿真循环、实体定义、机器人逻辑和 Tk UI 装配拆分为多个职责明确的模块，降低跨层修改时的联动风险。

## 当前结构

```text
main.py                  # 启动入口 + 兼容导出
app/
  bootstrap.py           # 应用装配
  context.py             # 初始仿真状态装配与定时启动
  logging_config.py      # 日志初始化与 logger 获取
simulation/
  astar.py               # A* 路径规划算法
  counting.py            # 垃圾收集计数器
  runtime.py             # 仿真运行时全局状态
  state.py               # 状态对象定义
  factory.py             # 创建/增删/重置世界对象
  engine.py              # 主循环、暂停、重置
  stats.py               # 统计数据计算
  passive_index.py       # 被动对象索引
robot/
  brain.py               # 机器人决策
  bot.py                 # 机器人实体编排
  sensing.py             # 传感器计算
  motion.py              # 差速运动与边界处理
  cleaning.py            # 清洁逻辑
  state_view.py          # 模式推导与状态映射
entities/
  cat.py                 # 猫实体
  charger.py             # 充电站实体
  dirt.py                # 垃圾实体
  lamp.py                # 灯实体
ui/
  window.py              # 画布初始化
  stats_panel.py         # 统计面板
  controls.py            # 速度控件与键盘绑定
  control_panel.py       # 操作按钮面板
  renderer.py            # 集中绘制实体
  theme.py               # 主题常量
  tooltip.py             # 工具提示
tests/
  test_regressions.py    # 回归测试集
logs/
  simulation.log         # 运行时文件日志（启动时自动创建）
```

## 模块边界

- `main.py`
  - 只保留入口和兼容导出，不再承载具体业务实现。
- `app/bootstrap.py`
  - 负责把 UI、状态、仿真循环装配到一起。
- `app/context.py`
  - 负责创建初始 `simulation_data`，应用 reset 结果并调度第一帧循环。
- `app/logging_config.py`
  - 负责日志双通道初始化，提供文件日志和控制台日志的独立级别配置，以及结构化事件日志输出。
- `simulation/*`
  - 负责世界状态、调度、对象生命周期和统计。
- `robot/*`
  - 负责机器人自身行为，不再混在 UI/入口文件中。
- `ui/*`
  - 负责 Tk 组件创建与绑定。
- `entities/*`
  - 负责独立环境实体定义。

## 兼容策略

为了不破坏现有回归测试和外部调用方式，`main.py` 仍然导出：

- `Bot`
- `Brain`
- `Lamp`
- `createObjects`
- `moveIt`
- `reset_simulation`
- `toggle_pause`
- `initialise`

这让项目内部已经完成拆分，同时保留原有使用入口。

## 当前收益

- 入口和 UI 装配与仿真逻辑分离。
- `main.py` 从超大单文件收敛为薄入口。
- 机器人逻辑按决策/传感/运动/清洁分块。
- 回归测试不再依赖真实 Tk 窗口启动。
- `Cat`、`Charger`、`Dirt` 已进入 `entities/`，根目录兼容包装已移除。
- 实体绘制逻辑集中在 `ui/renderer.py`，绘制实现不再散落在多个实体文件里。
- `app/bootstrap.py` 从 256 行降到 145 行，初始状态装配和控制面板已拆出。
- 普通运行日志不再直接 `print()` 到控制台，而是统一进入 `logs/simulation.log`。
- 控制台仅保留 `WARNING` / `ERROR` 级别，且文件级别和控制台级别可独立配置。
- UI 运行参数区已新增两个日志级别下拉框，可分别控制文件日志和控制台日志级别，并立即生效。
- 文件日志现在以 `tick=` 开头的单行键值对事件格式输出，适合按 `event=`、`bot=`、`cat=` 回看因果链排障。
- `robot/state_view.py` 负责把分散的布尔状态稳定映射为 `mode` 字符串，保证日志可搜索且一致。

## 后续可继续演进的方向

- 为 `simulation/state.py`、`simulation/factory.py` 和 `app/bootstrap.py` 增加更细粒度单测。
- 继续把 `Bot.draw()` 也迁入 renderer，彻底统一渲染出口。
- 视需要把 UI 回调继续从 `bootstrap.py` 下沉到单独 action/controller 模块。
- 如需长期运行仿真，可继续增加 UI 级日志级别切换和日志文件查看入口。
- 如需更进一步，可把当前日志级别显示到状态面板中，便于截图或演示时确认现场配置。
