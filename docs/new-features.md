# 新增功能说明

本文档记录在原始项目基础上新增的三个功能模块。

---

## 1. 结构化日志系统

### 背景

原始项目所有运行信息均通过 `print()` 直接输出到终端，调试信息、正常事件和错误信息混杂在一起，无法按级别过滤，也没有持久化记录，不利于长期运行后排障。

### 实现方案

新增 `app/logging_config.py`，引入双通道日志：

| 通道 | 目标 | 默认级别 | 格式 |
|------|------|---------|------|
| 文件 handler | `logs/simulation.log` | `INFO` | 时间戳 + 级别 + 模块名 + 消息 |
| 控制台 handler | `stderr` | `WARNING` | 精简格式 |

业务模块通过 `get_logger(__name__)` 获取 logger，统一使用 `sim` 命名空间，不污染 root logger。

### 日志级别策略

| 级别 | 用途 |
|------|------|
| `DEBUG` | 传感器诊断、内部状态切换、避让细节 |
| `INFO` | 对象创建/删除、开始充电、充满电、清洁完成、重置仿真 |
| `WARNING` | 无法找到路径、被占用资源等需要关注的运行退化 |
| `ERROR` | 仿真循环异常和不可恢复错误 |

### 事件日志格式

文件日志以结构化键值对格式输出，每行一个事件，便于 `grep` 排查因果链：

```
tick=142 event=charging_started bot=Bot-1 charger=Charger-2 battery=587
tick=143 event=path_not_found bot=Bot-1 reason=start_blocked
```

日志目录 `logs/` 在应用启动时自动创建，无需手动配置。

### 涉及模块

- `app/logging_config.py`（新增）
- `robot/brain.py`、`robot/bot.py`、`robot/cleaning.py`
- `entities/cat.py`
- `simulation/factory.py`、`simulation/engine.py`

---

## 2. UI 运行时日志级别控件

### 背景

日志系统上线后，每次调整调试粒度都需要修改代码或重启应用，在仿真运行中无法动态切换日志输出策略。

### 实现方案

在"仿真速度"右侧新增两个下拉框，构成运行参数区：

```
[ 仿真速度 ▼ ]  [ 文件日志 ▼ ]  [ 控制台日志 ▼ ]
```

下拉框选项统一为：`DEBUG` / `INFO` / `WARNING` / `ERROR`

**默认值：**
- 文件日志：`INFO`
- 控制台日志：`WARNING`

**运行时行为：**
- 修改任一下拉框后，对应 handler 的级别立即生效，无需重启仿真
- 两个通道相互独立，修改一个不影响另一个

### 涉及模块

- `app/logging_config.py`：新增运行时 level getter/setter
- `ui/controls.py`：新增日志级别控件构建函数
- `app/bootstrap.py`：将 UI 变更回调绑定到日志 setter

---

## 3. 机器人主动避猫

### 背景

原始实现中机器人完全不感知猫，只有猫在距离 < 30 时才触发 `jump_away()`，触发时机过晚。加之主循环先更新机器人再更新猫，猫往往在接触后才补救，机器人与猫经常发生碰撞。

### 根本原因

| 问题 | 说明 |
|------|------|
| 机器人不感知猫 | `Bot` 只有灯、机器人、杂物、充电站四类传感，无猫感知 |
| 猫反应过晚 | 触发距离仅 30，`jump_away()` 来不及躲开 |
| 调度顺序 | 先更新机器人后更新猫，补救总滞后一帧 |

### 实现方案

采用双边修复策略，机器人和猫两侧同时响应：

**猫侧：提前进入 panic jump**
- 新增 `panic_distance` 参数（远大于原 30 的阈值）
- `Cat.update()` 开头优先计算与最近机器人的距离
- 距离 < `panic_distance` 时立即触发 `jump_away()`，先于旧逻辑执行
- 猫感应消失后，`avoid_cat` 至少保持最短持续帧数再退出，避免反复横跳

**机器人侧：新增猫感知与避让决策**
- `robot/sensing.py` 新增 `sense_cats(sensor_positions, cats)` 方法，返回左右猫感应值
- `robot/brain.py` 新增避猫决策分支，决策优先级：
  1. 重叠分离（最高）
  2. 低电量充电硬约束
  3. 避猫 ← 新增
  4. 避杂物
  5. 避机器人
  6. 漫游（最低）
- 避猫时不维持全速直行，猫在正前方时减速偏转，一侧感应更强则向反方向转向

**调度层：主循环传入猫列表，并追加物理距离冻结**
- `simulation/engine.py` 主循环调用 `agent.thinkAndAct(agents, passiveObjects, cats)`，确保猫感知真正进入决策链路
- 由于前置传感器对侧后方存在盲区，主循环在每帧 `bot.update()` 之后额外计算所有 `(bot, cat)` 的环形最短物理距离
- 当距离 < `90px` 时，直接回退该帧机器人的位姿并强制 `sl/sr = 0`，记录 `bot.physical_cat_freeze`
- 这层保护不依赖传感器信号，作为避猫 steering 之外的最后一道硬约束，专门兜住跨边界、侧后方接近和多机器人夹击场景

### 涉及模块

- `entities/cat.py`：新增 `panic_distance`，提前触发 `jump_away()`
- `robot/sensing.py`：新增 `sense_cats()`
- `robot/brain.py`：新增避猫决策分支
- `robot/bot.py`：`thinkAndAct()` 新增 `cats` 参数
- `simulation/engine.py`：主循环传入 `cats` 列表，并增加基于环形最短距离的 `physical_cat_freeze`
