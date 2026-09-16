# Gather Workshop 增量需求（contract-v1）

本文件是本轮前后端实现的冻结契约。实现应沿用现有 React、TypeScript、FastAPI、单进程内存存储和全操作锁，不升级框架、不引入新依赖、数据库、认证或任务队列。

## 需求编号

- **R1 报名与候补**：有余位时新增记录为 `active`；满员时新增记录为 `waitlisted`。同一活动内，相同邮箱（去空格且不区分大小写）不能同时拥有多条 `active` 或 `waitlisted` 记录。
- **R2 退出与补位**：`active` 退出后保留为 `cancelled`，并在同一锁内将最早的有效候补晋升为 `active`；`waitlisted` 可以退出，退出后不得被自动安排回来；重复取消是无操作。
- **R3 容量调整**：容量使用绝对值设置，允许非负整数。增加容量时按候补顺序连续补位；减少容量不得低于当前 `active` 人数，也不得自动降级已确认人员。
- **R4 一致性**：活动卡片、详情统计和当前名单的人数应一致；并发或重复点击不能超额、重复占位或打乱候补顺序；不同活动互不影响。
- **R5 故障恢复**：保留现有写入前失败和写入后响应丢失模拟。前端不得自动重放写请求，应在失败后通过 GET 核对真实状态；人工重试不得产生重复记录、重新排队或二次补位。
- **R6 页面可用性**：工作人员能识别已报名、候补（含当前位次）和已退出记录，能够执行退出和容量调整，并收到明确的成功或失败反馈。

## 数据契约

`Registration.status` 允许：

- `active`
- `waitlisted`
- `cancelled`

保留现有 `Registration` 其他字段。候补序号不持久化，由同一活动内当前 `waitlisted` 记录的原始追加顺序计算。

已退出邮箱允许主动重新报名。新报名创建新记录，并按当时状态进入已报名或候补队尾；旧的 `cancelled` 记录继续保留。

## API 契约

### 新增报名

`POST /api/events/{event_id}/registrations`

- 请求：`{"name": string, "email": string}`
- 有余位：`201 Registration`，状态为 `active`
- 已满：`201 Registration`，状态为 `waitlisted`
- 相同邮箱已有 `active` 或 `waitlisted`：`409`

### 退出

`PATCH /api/events/{event_id}/registrations/{registration_id}`

- 请求：`{"status": "cancelled"}`
- 成功：`200 Registration`
- 已取消记录再次取消：返回当前记录，不再次补位
- 活动或活动内记录不存在：`404`

### 调整容量

`PATCH /api/events/{event_id}`

- 请求：`{"capacity": non-negative integer}`
- 成功：`200 Event`，包含最新 `activeCount`
- 新容量低于当前 `active` 人数：`409`，状态不变
- 相同容量：成功的无操作

## 调用与恢复约束

- `App.tsx` 不直接使用 `fetch`；所有 HTTP 调用由 `src/api.ts` 构造。
- 保留 `request<T>()` 对 `X-Demo-Fail` 的注入机制。
- 客户端不自动重试 POST、PATCH 或其他写请求。
- 所有需要“检查后修改”的后端操作必须完整处于 `store.lock` 内。
- 补位 helper 在调用方持锁时运行，不得重复获取现有非重入锁。
- `activeCount` 继续实时派生，不新增可漂移的计数字段。

## 文件与架构边界

- 后端增量限于 `api/app.py` 和 `api/tests/test_app.py`。
- 前端增量限于 `src/api.ts`、`src/App.tsx` 和 `src/styles.css`。
- 不修改依赖、锁文件、Vite 代理、端口、持久化约定或部署方式。
- 实现 agent 分别追加自己的工作日志；接口变更必须先由主 agent 更新本契约版本。

