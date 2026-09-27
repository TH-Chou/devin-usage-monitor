# Devin Token Monitor

**[简体中文](README.zh-CN.md)**

A native macOS app that monitors **local Devin CLI token usage** — a menu-bar
live cost display plus a Liquid Glass dashboard, installable as a `.dmg`.
Fully local and offline: it reads Devin's own `sessions.db` directly, with no
HTTP server, no account, and no data leaving your Mac.

## Features

- **Menu-bar presence** — today's estimated cost right in the status bar,
  with a drop-down summary; the window app lives in the Dock and stays alive
  when closed.
- **Full dashboard** — Overview / Models / Sessions / Requests / Settings in a
  native `NSWindow` (`WKWebView`, no web server): KPI cards, token & cost
  trend lines (24 h / 14 d), model cost donut, token composition, cache
  hit-rate, weekday×hour activity heatmap, top-session ranking, model
  cost/speed scatter, per-request latency / TTFT / tokens-per-second.
- **Cost estimation** — per-1M-token prices for ~140 models in an editable
  `prices.json` (input / output / cache-read / cache-write), with
  exact → prefix → family matching (e.g. `claude-sonnet-4-5-…` → sonnet
  price) and reasoning-effort suffixes.
- **Drill-down** — click a model, session or request to filter/expand; lazy
  loading of assistant response bodies keeps snapshots light.
- **Export** — one-click CSV zip (requests / sessions / daily / models) via a
  native save panel, ⌘E, or the web API.
- **Budget alert** — optional `daily_budget` posts a macOS notification and
  flags the window title once per day.
- **Six languages** — Chinese, English, Japanese, Korean, Spanish, Vietnamese;
  the persisted choice drives both the web view and the native chrome.
- **Auto-refresh** — incremental watermark polling of `sessions.db`
  (~15 s interval, full re-aggregation ≈ 0.3 s at launch).

## Install

Download `DevinTokenMonitor-<version>.dmg` from
[Releases](../../releases), open it, drag **Devin Token Monitor** into
`Applications`, and launch. The app is unsigned — if Gatekeeper warns,
right-click → Open.

Requires macOS 12+ and local Devin CLI data at
`~/.local/share/devin/cli/sessions.db` (created once you've used the Devin
CLI/agent).

## Build from source

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt

# run the native window app from source
.venv/bin/python -m devin_token_monitor.gui

# or the rumps menu-bar app (with embedded web dashboard on :7878)
./run.sh

# one-shot text report
.venv/bin/python -m devin_token_monitor.cli

# package .app + .dmg (self-contained, embeds Python and the icon)
./build_app.sh && ./build_dmg.sh

# optional: launch at login
./install_login_agent.sh           # remove: --remove
```

## How it works

Devin CLI persists every session message as JSON in
`~/.local/share/devin/cli/sessions.db` (SQLite, WAL mode). Assistant
reasoning messages carry `metadata.metrics` with `input_tokens`,
`output_tokens`, `cache_read_tokens`, `cache_creation_tokens`,
`generation_model`, `request_id` and timestamps. The monitor opens the
database **read-only**, polls incrementally on a `row_id` watermark, and
deduplicates replicated message-tree records by `request_id` (with a
`message_id` fallback).

The window app is plain PyObjC: `NSWindow` + `WKWebView` + `NSStatusItem`.
Each poll pushes a JSON snapshot into the page via `evaluateJavaScript`;
page actions (refresh, export, settings, language) come back through
`webkit.messageHandlers`.

> **Limitation:** Devin credits/ACU are server-side and are *not* in the local
> database — the app counts tokens and estimates cost from `prices.json`, so
> figures are approximations.

## Configuration

`prices.json` is resolved in order: `$DTM_PRICES` →
`~/.devin-token-monitor/prices.json` → bundled app resources → the copy in
this repo. `settings.daily_budget` enables the daily budget alert;
`settings.language` picks the UI language.

| Env var | Purpose | Default |
|---|---|---|
| `DEVIN_SESSIONS_DB` | Override `sessions.db` path | `~/.local/share/devin/cli/sessions.db` |
| `DTM_PORT` / `DTM_HOST` | Web dashboard bind (menu-bar mode) | `7878` / `127.0.0.1` |
| `DTM_PRICES` | Override `prices.json` path | auto-detected |

## Privacy

Everything stays on your Mac: the database is opened read-only, snapshots
never leave the process, and the only external interaction is an optional
`osascript` budget notification.

## Project layout

```
devin_token_monitor/
  db.py          read-only sessions.db access + row fetch
  pricing.py     price-table loading & cost math (multi-path resolution)
  aggregator.py  watermark-based incremental aggregation
  dashboard.py   shared dashboard page (web & app frontends)
  exporter.py    CSV export (requests/sessions/daily/models)
  web.py         stdlib HTTP server + JSON API (menu-bar mode)
  gui.py         native window app (NSWindow + WKWebView + status item)
  app.py         rumps menu-bar app (embeds the web server)
  cli.py         one-shot text report
gui_entry.py     py2app entry point   setup_gui.py   py2app config + icon
tools/           programmatic icon generator (PIL)
assets/          AppIcon.icns + source PNGs
build_app.sh     build .app           build_dmg.sh   build the DMG
prices.json      editable price table (+ settings.daily_budget / language)
PLAN.md          roadmap              AGENTS.md      dev notes
```

## License

[Apache-2.0](LICENSE)
