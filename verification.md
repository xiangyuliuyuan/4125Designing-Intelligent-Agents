# Verification

## 2026-04-05

### 执行命令

```bash
python3 -m unittest -v
python3 -m compileall main.py app/ simulation/ robot/ entities/ ui/ tests/
```

### 结果

- 46/46 tests passed
- `compileall` passed for `main.py`, `app/`, `simulation/`, `robot/`, `entities/`, `ui/` and existing root modules
- 入口委托测试通过：`main.main()` 不再直接拉起真实 Tk，而是委托 `run_app()`
- 机器人充电、路径规划、重叠分离、垃圾清洁、重置和统计相关回归全部通过
- `entities` 包导出、renderer 绘制、context 装配和 control panel 构建新增回归全部通过
- 日志分流新增回归通过：`INFO` 进入文件、`WARNING` 同时进入文件和控制台，重复初始化不重复挂 handler
- UI 日志控件新增回归通过：默认值正确，变更文件级别和控制台级别时能够独立更新 handler
- 避猫修复新增回归通过：猫会在 `panic_distance` 内提前跳离，机器人接收到猫感应后不再维持全速直行，主循环会把 `cats` 传入机器人决策
- 结构化事件日志新增回归通过：日志文件写入 `tick=... event=...` 纯键值对格式，mode 推导优先级稳定
- 避猫持续性修复新增回归通过：猫感应消失后，`avoid_cat` 会至少保持一段最短持续帧数，再退出
- 避猫动作强化新增回归通过：猫感应在旧阈值以下也能触发避猫，且动作升级为强原地转向

### 已验证风险

- 模块拆分后，原有关键行为未回归
- `initialise()` 仍然对顶层窗口设置 `resizable(False, False)`
- `moveIt()` 在不同速度下仍然保持单帧 `dt=1.0`
- 共享仿真时间仍然作用于液体垃圾冷却逻辑
- 根目录实体模块改为兼容包装后，现有入口和测试访问方式未被破坏
- 日志配置默认在应用启动时初始化，日志目录 `logs/` 会在运行时自动创建

### 备注

- 当前验证以 `unittest` 回归集为主，未额外引入静态检查工具
- 测试输出中仍包含业务 `print()` 日志，这不影响通过结果
