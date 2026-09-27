# Devin Token Monitor

**[English](README.md)**

原生 macOS 桌面应用（可安装 DMG），监控**本地 Devin CLI 的 token 用量** ——
菜单栏实时显示今日费用 + Liquid Glass 仪表盘。完全本地离线：直接只读 Devin
自己的 `sessions.db`，不开 HTTP 服务，不需要账号，数据不出本机。

## 功能

- **菜单栏常驻** —— 状态栏实时显示今日估算费用，下拉看摘要；窗口 App 在 Dock
  常驻，关窗不退出。
- **完整仪表盘** —— 原生 `NSWindow`（`WKWebView`，无 HTTP 服务）内分
  概览 / 模型 / 会话 / 请求 / 设置：KPI 卡片、token 与费用趋势（近 24h / 近
  14 天）、模型费用环形图、token 构成、缓存命中率、星期×小时活动热力图、
  会话成本排行、模型 成本/速度 散点图、单请求 延迟 / TTFT / tokens/s。
- **费用估算** —— `prices.json` 可编辑，内置约 140 个模型的每 1M token 单价
  （input / output / cache_read / cache_creation），按 精确 → 前缀 → 族名
  匹配（如 `claude-sonnet-4-5-…` → sonnet 价），支持 reasoning-effort 后缀。
- **下钻** —— 点模型 / 会话 / 请求即可筛选展开；assistant 响应体按需懒加载，
  快照保持轻量。
- **导出** —— 一键导出 CSV zip（requests / sessions / daily / models），走原生
  保存面板，也可 ⌘E 或走 Web API。
- **预算告警** —— 可选 `daily_budget`，超预算时弹 macOS 通知并改窗口标题
  （每天一次）。
- **六种语言** —— 中文、English、日本語、한국어、Español、Tiếng Việt；
  选择持久化到 `prices.json`，页面与原生界面同时生效。
- **自动刷新** —— 对 `sessions.db` 做 `row_id` 水位线增量轮询（约 15 秒一次，
  启动时全量聚合约 0.3 秒）。

## 安装

从 [Releases](../../releases) 下载 `DevinTokenMonitor-<版本>.dmg`，打开后把
**Devin Token Monitor** 拖进 `Applications` 启动。App 未签名，若 Gatekeeper
拦截请右键 → 打开。

要求 macOS 12+，且本机已用过 Devin CLI（数据在
`~/.local/share/devin/cli/sessions.db`）。

## 源码构建

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt

# 从源码跑原生窗口 App
.venv/bin/python -m devin_token_monitor.gui

# 或 rumps 菜单栏版（内嵌 Web 仪表盘 http://127.0.0.1:7878）
./run.sh

# 一次性文本报表
.venv/bin/python -m devin_token_monitor.cli

# 打 .app + .dmg（自包含，内嵌 Python 与图标）
./build_app.sh && ./build_dmg.sh

# 可选：登录自启动
./install_login_agent.sh           # 卸载：--remove
```

## 工作原理

Devin CLI 把每条会话消息以 JSON 存在
`~/.local/share/devin/cli/sessions.db`（SQLite，WAL 模式）。assistant 推理
消息的 `metadata.metrics` 里有 `input_tokens`、`output_tokens`、
`cache_read_tokens`、`cache_creation_tokens`、`generation_model`、
`request_id` 和时间戳。监控器以**只读**方式打开数据库，按 `row_id` 水位线
增量拉取，并按 `request_id` 去重复制的消息树记录（`message_id` 兜底）。

窗口 App 是纯 PyObjC：`NSWindow` + `WKWebView` + `NSStatusItem`。每轮轮询把
JSON 快照 `evaluateJavaScript` 推进页面，页面动作（刷新、导出、设置、语言）
经 `webkit.messageHandlers` 回传。

> **限制**：Devin credits/ACU 是服务端数据，不在本地库里 —— 只能统计 token，
> 费用是按 `prices.json` 估算的近似值。

## 配置

`prices.json` 按顺序解析：`$DTM_PRICES` → `~/.devin-token-monitor/prices.json`
→ App 内置资源 → 本仓库文件。`settings.daily_budget` 开启预算告警；
`settings.language` 选择界面语言。

| 环境变量 | 作用 | 默认 |
|---|---|---|
| `DEVIN_SESSIONS_DB` | 覆盖 sessions.db 路径 | `~/.local/share/devin/cli/sessions.db` |
| `DTM_PORT` / `DTM_HOST` | Web 仪表盘绑定（菜单栏模式） | `7878` / `127.0.0.1` |
| `DTM_PRICES` | 覆盖 prices.json 路径 | 自动探测 |

## 隐私

一切留在本机：数据库只读打开，快照不出进程，唯一的对外动作是可选的
`osascript` 预算通知。

## 项目结构

```
devin_token_monitor/
  db.py          sessions.db 只读访问 + 行拉取
  pricing.py     价格表加载与费用计算（多路径解析）
  aggregator.py  水位线增量聚合（模型/会话/天 + 请求队列）
  dashboard.py   共享仪表盘页面（web/app 两个前端共用）
  exporter.py    CSV 导出（requests/sessions/daily/models）
  web.py         stdlib HTTP 服务 + JSON API（菜单栏模式）
  gui.py         原生窗口 App（NSWindow + WKWebView + 状态栏）
  app.py         rumps 菜单栏 App（内嵌 Web 服务）
  cli.py         一次性文本报表
gui_entry.py     py2app 入口          setup_gui.py   py2app 配置 + 图标
tools/           PIL 程序化图标生成
assets/          AppIcon.icns + 源 PNG
build_app.sh     打 .app              build_dmg.sh   打 DMG
prices.json      可编辑价格表（settings.daily_budget / language）
PLAN.md          迭代计划             AGENTS.md      开发约定
```

## 许可证

[Apache-2.0](LICENSE)
