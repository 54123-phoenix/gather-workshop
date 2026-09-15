# Gather

一个可以本地运行的社区活动报名工作台，使用 React、TypeScript 和 FastAPI。

这是独立编写的面试练习项目。所有活动、人员和邮箱均为虚构，不包含公司业务代码或客户资料；候选人的实现仅用于面试评估，不用于商业交付。

## 启动

需要 Node.js 20+、pnpm 9+ 和 uv。Python 3.11+ 可由 uv 自动准备。请在面试计时前完成安装并确认页面可打开。

```sh
pnpm install --frozen-lockfile
pnpm run setup:api
pnpm dev
```

打开 **http://127.0.0.1:5177**。前端使用 5177，后端使用 8765；请确保两个端口没有被占用。按 Ctrl+C 停止。若缺 pnpm，可先执行 `npm install -g pnpm@9.15.9`；uv 安装方法见 <https://docs.astral.sh/uv/getting-started/installation/>。

`pnpm dev` 会同时启动网页和 API，前后端保存代码后都会自动重载。当前示例刻意使用单进程内存存储，不需要数据库、Docker、账号、密钥或外部 AI 服务。后端重载或重启会恢复初始数据；单纯刷新网页不会清空数据。

## 现有功能

- 切换三个活动，查看名额与报名名单。
- 添加报名，校验输入、重复报名和满员。
- 刷新列表；刷新浏览器后能重新读取同一个运行中的 API 数据。
- 页面底部“演示工具”可以模拟写入失败和恢复初始数据。

开启“模拟写入失败”后，所有经统一请求函数发送的写请求会携带 `X-Demo-Fail: 1`；API 在修改数据前返回 503。关闭后恢复正常。恢复数据本身也是写请求，需要先关闭该选项。

## 验证

```sh
pnpm typecheck
pnpm test
pnpm build
# 或一次执行全部检查
pnpm check
```

现有后端测试只覆盖已经提供的功能。新增功能需要新增验证，现有测试全绿本身不能证明新增功能完成。前端目前提供类型和构建检查，交互结果需在页面中验证，也可以自行添加自动化测试。

## 结构

```text
src/App.tsx        页面、交互和本地状态
src/api.ts         API 数据类型、请求函数、故障开关
src/styles.css     页面样式
api/app.py        FastAPI 路由、内存存储与种子数据
api/tests/        现有功能测试
scripts/dev.mjs   同时启动两个本地服务
docs/architecture.md  数据与接口说明
```

API 交互文档：<http://127.0.0.1:8765/docs>。

本项目没有登录和权限模型，只能用作本地练习，不应作为公开部署服务。面试任务在计时开始时单独提供；允许使用你熟悉的 AI 工具及搜索。
