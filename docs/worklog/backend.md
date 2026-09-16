# Backend Worklog

本日志由后端实现 agent 追加维护。历史条目不得覆盖或删除。

## 条目格式

`BE-NNN | 时间 | contract-v1`

- 目标
- 修改文件
- 接口/行为决定
- 验证命令与结果
- 已知问题
- 下一步

## BE-001 | 2026-09-16 14:24:32 +08:00 | contract-v1

- 目标：核对冻结契约、现有数据路径、锁边界和故障模拟语义。
- 修改文件：`docs/worklog/backend.md`。
- 接口/行为决定：沿用单文件 `MemoryStore`；报名、取消、补位和容量调整的检查与写入全部位于现有 `store.lock` 内；候补顺序使用 `registrations` 原始追加顺序；`activeCount` 继续实时派生。
- 验证命令与结果：完整阅读 README、REQUIREMENTS、架构说明、后端实现与基线测试；契约与现有架构兼容，无需新增依赖或分层。
- 已知问题：现有满员行为仍返回 409，尚无退出和容量修改接口；现有并发测试断言需按候补新语义更新。
- 下一步：实现 contract-v1 状态模型、取消/补位 helper 和容量接口。

## BE-002 | 2026-09-16 14:31:00 +08:00 | contract-v1

- 目标：完成状态模型、报名候补、退出补位和绝对容量设置接口。
- 修改文件：`api/app.py`、`docs/worklog/backend.md`。
- 接口/行为决定：新增仅允许 `cancelled` 的更新模型和非负容量模型；有效重复邮箱检查覆盖 `active`/`waitlisted`；满员报名追加为 `waitlisted`；取消 active 后及扩容后均调用持锁 FIFO 补位 helper；重复取消与相同容量为无操作。
- 验证命令与结果：人工检查所有“检查后修改”路径均在 `store.lock` 内，补位 helper 不获取锁，响应中的 `activeCount` 实时计算。
- 已知问题：尚未通过自动化测试验证并发、故障响应丢失和边界输入。
- 下一步：更新回归测试并覆盖 contract-v1 的并发与故障场景。

## BE-003 | 2026-09-16 14:31:01 +08:00 | contract-v1

- 目标：覆盖候补、退出补位、容量调整、活动隔离、并发和故障响应丢失。
- 修改文件：`api/tests/test_app.py`、`docs/worklog/backend.md`。
- 接口/行为决定：更新原“满员返回 409”和“并发超额请求返回 409”的旧断言为候补语义；补充严格非负整数容量校验、跨活动记录归属校验，以及取消/容量写入的 before/after 故障验证。
- 验证命令与结果：聚焦运行 `uv run --project api pytest api/tests/test_app.py -q -k "cancel or capacity or waitlist or concurrent"`，15 passed、11 deselected；首次沙箱内运行因共享 uv 缓存无访问权限失败，获准使用现有 uv 流程后成功，期间 uv 自动准备了被 Git 忽略的 `api/.venv`。
- 已知问题：Starlette TestClient 报告一条上游 anyio 别名弃用警告，不影响测试结果，且本轮不升级依赖。
- 下一步：运行完整后端回归和差异检查。

## BE-004 | 2026-09-16 14:32:00 +08:00 | contract-v1

- 目标：完成后端最终验证与交付核对。
- 修改文件：`api/app.py`、`api/tests/test_app.py`、`docs/worklog/backend.md`。
- 接口/行为决定：contract-v1 后端接口保持冻结，无契约变更；所有派生人数与补位结果均以服务端锁内真实状态为准。
- 验证命令与结果：`uv run --project api pytest api/tests -q` 两次均为 26 passed、1 个非阻塞弃用警告；`git diff --check -- api/app.py api/tests/test_app.py` 通过（仅提示 Windows 后续可能转换行尾）。
- 已知问题：后端未进行浏览器端到端验证，该项由集成/review agent 负责；无未验证的后端契约风险。
- 下一步：交由主 agent 和 review agent 做前后端集成、页面验证与演示核对。
