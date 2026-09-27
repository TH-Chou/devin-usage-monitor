<div align="center">
  <img src="assets/banner.png" alt="Devin Token Monitor" width="100%">

  <p>
    <a href="https://github.com/TH-Chou/devin-usage-monitor/releases"><img alt="release" src="https://img.shields.io/github/v/release/TH-Chou/devin-usage-monitor?color=5b6cff&label=release"></a>
    <img alt="platform" src="https://img.shields.io/badge/native%20app-macOS%2012%2B-000000?logo=apple&logoColor=white">
    <img alt="python" src="https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white">
    <img alt="license" src="https://img.shields.io/badge/license-Apache--2.0-blue">
  </p>

  <p>
    <a href="README.md">English</a> · <b>简体中文</b>
  </p>

  <p><i>监控本地 Devin CLI token 用量与估算费用 ——<br>
  可选原生 macOS App，或直接集成到 VS Code 系列桌面 IDE。</i></p>
</div>

---

## 为什么做这个

Devin CLI 把每条请求的 token 指标都写进了本地 SQLite 数据库 —— 但没有
任何界面让你**看见**它们。Devin Token Monitor 把这些数据变成一目了然的
花费图景：完全本地、只读、无服务器、无需账号，数据不出本机。

## 功能一览

| | |
|---|---|
| **菜单栏实时费用** | 状态栏直接显示今日估算费用，点开看摘要；关窗不退出，菜单或 Dock 随时重开。 |
| **Liquid Glass 仪表盘** | 原生 `NSWindow` + `WKWebView`（无 HTTP 服务）：KPI 卡片、token/费用趋势（近 24h / 14 天）、模型环形图、token 构成、缓存命中率、星期×小时热力图、会话成本排行、成本/速度散点图。 |
| **单请求明细** | 模型、延迟、TTFT、tokens/s、单次费用——点任意模型/会话/请求下钻；响应体懒加载，快照保持轻量。 |
| **可编辑价格表** | `prices.json` 内置约 140 个模型的每 1M input/output/cache 单价；精确 → 前缀 → 族名匹配，支持 reasoning-effort 后缀。 |
| **预算告警** | 可选 `daily_budget`，超预算时每天一次 macOS 通知。 |
| **CSV 导出** | requests / sessions / daily / models，原生保存面板、⌘E 或 Web API。 |
| **六种语言** | 中文 · English · 日本語 · 한국어 · Español · Tiếng Việt —— 持久化保存，页面与原生界面同时生效。 |
| **自动刷新** | `row_id` 水位线增量轮询（约 15s）；启动时全量聚合约 0.3s。 |
| **IDE 扩展** | 面向桌面版 VS Code 和兼容 IDE 的 VSIX：状态栏费用、仪表盘 Webview、数据库选择、价格表编辑与 CSV 导出。 |
| **六套主题** | 跟随系统、午夜蓝、石墨、暖纸、深海、森林；选择会持久化。 |
| **Token 深度分析** | 7/30 天与本月至今统计、月末消耗趋势预测、缓存节省估算、输出效率、模型对比及请求规模/延迟 P50/P90 分位。 |
| **本地数据可靠性** | 只读 SQLite 支持含特殊字符的路径和数据库轮换检测；来源状态会提示轮询错误，设置写入用户目录而非安装包。 |

## 安装

从 [**Releases**](https://github.com/TH-Chou/devin-usage-monitor/releases)
下载 `DevinTokenMonitor-<版本>.dmg`，拖进 `Applications` 启动。
应用未签名 —— 首次打开请右键 → **打开**。

> **要求**：macOS 12+，且本机已有 Devin CLI 数据
> （`~/.local/share/devin/cli/sessions.db`，用过 Devin 即有）。

## VS Code 系列 IDE

从源码构建并安装 VSIX：

```bash
cd vscode-extension
npm install
npm run package
code --install-extension devin-token-monitor-0.3.0.vsix
```

随后在命令面板运行 **Devin Token Monitor: Open Dashboard**。要求本机 Python 3.10+。Cursor 支持 VSIX 兼容扩展；Windsurf 和其他分支版本的兼容性取决于其当前 VS Code API 与扩展安装策略。浏览器版 VS Code（`vscode.dev` / `github.dev`）不支持，因为它不能启动本机 Python worker 或访问本地 SQLite 数据库。详见 [`vscode-extension/README.md`](vscode-extension/README.md) 和[兼容性调研](vscode-extension/RESEARCH.md)。

## macOS App 源码构建

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt

.venv/bin/python -m devin_token_monitor.gui   # 原生窗口 App
./run.sh                                       # 菜单栏版 + Web 仪表盘 (:7878)
.venv/bin/python -m devin_token_monitor.cli   # 一次性文本报表

./build_app.sh && ./build_dmg.sh              # 打包 .app + .dmg
./install_login_agent.sh                       # 可选：登录自启动（--remove 卸载）
```

## 工作原理

Devin CLI 将每条会话消息以 JSON 存入
`~/.local/share/devin/cli/sessions.db`（SQLite，WAL）。assistant 推理消息
的 `metadata.metrics` 包含 `input_tokens`、`output_tokens`、
`cache_read_tokens`、`cache_creation_tokens`、`generation_model`、
`request_id` 和时间戳。监控器以**只读**方式打开数据库，按 `row_id`
水位线增量拉取，并按 `request_id` 去重复制记录（`message_id` 兜底）。

原生 App 通过 `evaluateJavaScript` 推送快照，页面动作经
`webkit.messageHandlers` 回传。IDE 扩展由本机 Node 扩展宿主启动随包
Python worker，通过 stdio 上的 JSON Lines 通信；复用相同的聚合模块和仪表盘，
不监听本地 HTTP 端口。

> **说明**：Devin credits/ACU 在服务端，不在本地库中 —— 本应用统计
> token 并按 `prices.json` **估算**费用。

## 配置

`prices.json` 按顺序读取：`$DTM_PRICES` → `~/.devin-token-monitor/prices.json`
→ App 内嵌资源 → 仓库文件。首次修改时会复制到可写的用户文件，绝不改写已安装
App 包内资源。`settings.daily_budget` 开启预算告警；`settings.language` 和
`settings.theme` 保存语言与主题偏好。

| 环境变量 | 作用 | 默认 |
|---|---|---|
| `DEVIN_SESSIONS_DB` | 覆盖数据库路径 | `~/.local/share/devin/cli/sessions.db` |
| `DTM_PORT` / `DTM_HOST` | Web 仪表盘绑定（菜单栏模式） | `7878` / `127.0.0.1` |
| `DTM_PRICES` | 覆盖 `prices.json` 路径 | 自动探测 |

## 隐私

一切留在本机：数据库只读打开，快照不出进程，唯一对外动作是可选的
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
vscode-extension/ VS Code 系列 IDE VSIX（Node 宿主 + Python worker）
gui_entry.py     py2app 入口            setup_gui.py   py2app 配置 + 图标
tools/           PIL 图标与头图生成器
assets/          AppIcon.icns、源 PNG、README 头图
build_app.sh     打 .app                build_dmg.sh   打 DMG
prices.json      可编辑价格表（含 settings）
```

## 许可证

[Apache-2.0](LICENSE)
