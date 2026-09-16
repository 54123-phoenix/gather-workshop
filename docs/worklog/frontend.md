# Frontend Worklog

本日志由前端实现 agent 追加维护。历史条目不得覆盖或删除。

## 条目格式

`FE-NNN | 时间 | contract-v1`

- 目标
- 修改文件
- 接口/行为决定
- 验证命令与结果
- 已知问题
- 下一步

## FE-001 | 2026-09-16 | contract-v1

- 目标：完成前端基线理解，确认最小增量位置与文件边界。
- 修改文件：`docs/worklog/frontend.md`。
- 接口/行为决定：保留 `src/api.ts` 的统一 `request<T>()` 与故障头注入；在 `App.tsx` 现有状态模型内增加名单派生统计、退出、绝对容量设置和失败后 GET 核对；不拆组件、不引入新依赖。
- 验证命令与结果：已完整阅读 README、冻结契约、架构说明、三个前端源文件和日志；确认当前页面已有旧响应保护、全局 busy、错误/成功消息与刷新机制可复用。
- 已知问题：当前类型缺少 `waitlisted`；页面仅支持新增报名；写失败后不会读取核对；卡片与详情人数来自活动接口，可能与名单读取时点不一致。
- 下一步：先补齐 API 类型化调用，再实现页面行为。

## FE-002 | 2026-09-16 | contract-v1

- 目标：补齐 contract-v1 的前端数据类型与写操作调用。
- 修改文件：`src/api.ts`、`docs/worklog/frontend.md`。
- 接口/行为决定：`Registration.status` 增加 `waitlisted`；新增 `cancelRegistration()` 与 `updateEventCapacity()`，均复用现有 `request<T>()`，不增加任何自动重试。
- 验证命令与结果：静态核对两个 mutation 均使用 PATCH、JSON 请求体和冻结路径；`App.tsx` 后续只需调用导出函数，不直接使用 `fetch`。
- 已知问题：页面尚未接入新调用，也尚未运行类型检查。
- 下一步：实现统计、名单状态、退出、容量调整及失败后刷新。

## FE-003 | 2026-09-16 | contract-v1

- 目标：完成名单、退出、容量调整与当前活动统计的页面增量。
- 修改文件：`src/App.tsx`、`src/styles.css`、`docs/worklog/frontend.md`。
- 接口/行为决定：当前活动卡片和详情统计统一由当前名单派生；候补位次按原始记录顺序计算；退出与容量设置只调用 API 层 mutation；三种写操作成功后刷新，失败后也仅以 GET 刷新核对，不在客户端推断晋升结果。
- 验证命令与结果：静态搜索确认 `App.tsx` 无直接 `fetch`，新增报名、退出和容量调整全部通过 `src/api.ts`；名单保留原始顺序并展示三种状态、候补位次和可用退出按钮。
- 已知问题：`pnpm typecheck` 由包管理器报 `[ERROR] fetch failed`，尚未得到 TypeScript 编译结果；需要继续执行构建并人工复核响应式样式。
- 下一步：完成构建尝试、源代码复核和故障恢复静态检查。

## FE-004 | 2026-09-16 | contract-v1

- 目标：完成故障恢复、调用边界和响应式增量的最终前端验证。
- 修改文件：`src/api.ts`、`src/App.tsx`、`src/styles.css`、`docs/worklog/frontend.md`。
- 接口/行为决定：所有 mutation 失败后仅触发现有 GET 刷新；活动切换时清空上一场名单标识并同步目标活动容量；保留 effect cleanup，旧读取响应不能覆盖新活动；当前活动人数只取当前名单，其他活动卡片继续取活动接口。
- 验证命令与结果：`rg` 确认 `fetch` 只存在于 `src/api.ts` 的统一请求函数；`git diff --check` 通过（仅报告仓库既有的 LF/CRLF 转换提示）。`pnpm typecheck` 与 `pnpm build` 均在约 60 秒后由包管理器返回 `[ERROR] fetch failed`；检查确认本地不存在 `node_modules`、TypeScript 与 Vite 可执行文件，因此未安装依赖，也未绕过项目约束。
- 已知问题：未获得 TypeScript 编译、生产构建或浏览器交互结果；需在依赖就绪后由集成/review agent 补跑。页面样式已按现有 1100px 与 760px 断点扩展，但尚未进行实际浏览器视觉核对。
- 下一步：交由主 agent 与 review agent 在后端合入、依赖就绪后执行全量检查和页面验收。
