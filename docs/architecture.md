# 项目与接口说明

Gather 是虚构的社区活动报名管理场景。基线交付物包括可运行网页、API、演示数据和现有行为的回归测试。新增面试需求单独提供。

## 数据

`Event` 包含 id、title、category、date、time、location、capacity、activeCount、description。

`Registration` 包含 id、eventId、name、email、status、createdAt。status 允许 `active` 和 `cancelled`。目前初始记录全部为 active；人数由每个活动的 active 记录实时计算。

人物、地点、活动、邮箱均从零编造。数据保存在服务进程的内存字典内，写操作由锁保护。单个进程运行，不涉及分布式并发、持久化数据库或迁移。

## 接口

| 方法 | 路径 | 行为 |
| --- | --- | --- |
| GET | `/api/health` | 服务健康检查 |
| GET | `/api/events` | `{items: Event[]}` |
| GET | `/api/events/{id}/registrations` | `{items: Registration[]}` |
| POST | `/api/events/{id}/registrations` | 输入 `{name, email}`，201 返回一条报名 |
| POST | `/api/demo/reset` | 恢复种子数据，返回 `{ok: true}` |

不存在的活动返回 404；相同活动内已经有效报名的邮箱不能重复报名（不区分大小写），返回 409；满员返回 409；非法输入返回 422。

携带 `X-Demo-Fail: 1` 的写请求在执行前返回 503，不应改变任何状态。这是明确的本地演示开关，用于检查失败提示与恢复行为。

## 网页

前端通过 Vite 将 `/api` 代理到本地后端，不需要 CORS 配置。`src/api.ts` 是统一请求入口；页面依据真实 API 结果显示状态。切换活动会重新请求对应数据，旧读取响应不能覆盖新选中的活动。

## 验收与边界

基线要求：三个活动可读取；添加后人数增加且刷新仍存在；重复或满员请求被拒绝且人数不变；故障开关返回错误且不写入；重置恢复种子数据。类型检查、后端测试和构建命令见 README。

不涉及登录、支付、通知、真实邮件、部署或第三方模型调用。无需为面试增加这些能力。
