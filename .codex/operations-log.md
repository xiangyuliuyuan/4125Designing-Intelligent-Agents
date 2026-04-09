# Operations Log

## 2026-04-05

- 读取项目结构，确认这是非 Git 仓库的 Python Tkinter 单体项目。
- 识别 `main.py` 为核心耦合点，承担实体、UI、仿真循环和入口多重职责。
- 基线测试执行发现真实 Tk 初始化在当前 macOS/Tk 环境下崩溃，需将入口测试改为 mock 边界测试。
- 决定采用“状态层 + 仿真层 + 机器人层 + UI 层”的渐进式重构方案。
- 写入设计文档 `docs/superpowers/specs/2026-04-05-simulation-refactor-design.md`。
- 写入实施计划 `docs/superpowers/plans/2026-04-05-simulation-refactor.md`。
- 新建 `app/`, `simulation/`, `robot/`, `entities/`, `ui/` 模块目录并完成首轮代码迁移。
- 将 `main.py` 收口为兼容导出层和启动入口，保留原测试访问面。
- 将 `main()` 相关回归测试改为 fake Tk 边界测试，移除对真实 GUI 初始化的依赖。
- 完整执行 `python3 -m unittest -v`，33/33 通过。
- 第二轮拆分：新增 `entities/cat.py`, `entities/charger.py`, `entities/dirt.py`，根目录同名文件改为兼容包装。
- 第二轮拆分：新增 `ui/renderer.py`，集中实体绘制逻辑；`Lamp` 也已接入 renderer。
- 第二轮拆分：新增 `app/context.py` 和 `ui/control_panel.py`，继续拆薄 `app/bootstrap.py`。
- 第二轮新增 4 条回归测试，完整执行 `python3 -m unittest -v`，37/37 通过。
- 执行 `python3 -m compileall main.py app simulation robot entities ui astar.py cat.py charger.py counting.py dirt.py` 通过。
- 新增 `app/logging_config.py`，建立 `sim` 日志命名空间和双 handler 结构。
- 普通运行日志改为写入 `logs/simulation.log`，控制台默认仅输出 `WARNING` / `ERROR`。
- 清理所有业务 `print()`，统一迁移到 `logger.debug/info/warning/exception`。
- 新增 2 条日志配置回归测试，完整执行 `python3 -m unittest -v`，39/39 通过。
- 在运行参数区新增两个日志级别下拉框，分别控制文件日志和控制台日志。
- 为日志控件新增 2 条回归测试，完整执行 `python3 -m unittest -v`，41/41 通过。
- 定位“机器人仍会撞猫”的根因：机器人不感知猫、猫的 jump 触发过晚、主循环未把猫传给机器人决策。
- 新增猫 panic jump、机器人猫感知和避猫决策，并把 `cats` 接入 `moveIt()` 的 `thinkAndAct()` 调用链路。
- 新增 3 条避猫回归测试，完整执行 `python3 -m unittest -v`，43/43 通过。
- 将文件日志升级为结构化事件日志：统一 `tick=` 开头、单行键值对、不带时间戳和 logger 前缀。
- 新增 `robot/state_view.py` 统一推导 bot/cat mode，供事件日志稳定引用。
- 将关键事件链路接入日志：低电量、重规划、充电、等待、避猫、重叠、异常、控制动作。
- 新增结构化日志与 mode 推导回归测试，完整执行 `python3 -m unittest -v`，44/44 通过。
- 根据实际运行日志复盘避猫问题，确认 `cat.panic_jump` 已在 77.17 距离触发，说明 `panic_distance` 已生效。
- 为 `avoid_cat` 增加最短持续帧数，避免猫瞬移后机器人在下一帧假性退出避猫。
- 新增最短持续帧数回归测试，完整执行 `python3 -m unittest -v`，45/45 通过。
- 继续根据运行日志收敛剩余根因：确认 `panic_distance` 生效后，主要问题转为 `avoid_cat` 触发偏晚、动作偏弱。
- 将 `cat_avoid_threshold` 下调，并把避猫动作改为更强的原地转向，避免机器人在避猫期间继续向前推进。
- 新增“低于旧阈值也能触发避猫且原地转向”的回归测试，完整执行 `python3 -m unittest -v`，46/46 通过。
