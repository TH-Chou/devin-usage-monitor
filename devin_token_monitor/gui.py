"""Native macOS window app for Devin token monitoring.

A real NSWindow hosting a WKWebView that renders the shared dashboard
page, plus an NSStatusItem menu-bar presence.  No HTTP server: the app
polls ``sessions.db`` and pushes each snapshot straight into the page via
``evaluateJavaScript('update(...)')``; the page calls back through
``webkit.messageHandlers.dtm`` (refresh / export / settings / login item).

Run:  .venv/bin/python -m devin_token_monitor.gui
Packaged: see build_app.sh / build_dmg.sh
"""

from __future__ import annotations

import functools
import json
import os
import subprocess
import sys
import threading
import zipfile
from datetime import date
from pathlib import Path

import objc
import AppKit as AK
from AppKit import (
    NSApplication,
    NSApplicationActivationPolicyRegular,
    NSApp,
    NSBackingStoreBuffered,
    NSEvent,
    NSMenu,
    NSMenuItem,
    NSModalResponseOK,
    NSSavePanel,
    NSStatusBar,
    NSWindow,
    NSWindowStyleMaskClosable,
    NSWindowStyleMaskMiniaturizable,
    NSWindowStyleMaskResizable,
    NSWindowStyleMaskTitled,
)

NSWindowStyleMaskFullSizeContentView = 1 << 15
NSWindowTitleHidden = 1
from Foundation import (
    NSBundle,
    NSMakeRect,
    NSMakeSize,
    NSObject,
    NSTimer,
)
from WebKit import WKWebView, WKWebViewConfiguration

from . import __version__
from .aggregator import UsageAggregator
from .dashboard import PAGE
from .db import db_path
from .exporter import export_all
from .pricing import PriceTable, default_prices_path, editable_prices_path

POLL_SECONDS = 15
LOGIN_AGENT_LABEL = "com.local.devin-token-monitor"
NSVariableStatusItemLength = -1.0

_delegate = None  # keep a strong ref; NSApplication.delegate is weak


def _login_plist_path() -> Path:
    return (
        Path.home()
        / "Library"
        / "LaunchAgents"
        / f"{LOGIN_AGENT_LABEL}.plist"
    )


def _login_item_installed() -> bool:
    return _login_plist_path().exists()


def _write_login_item() -> None:
    bundle = NSBundle.mainBundle().bundlePath()
    if bundle.endswith(".app"):
        exe = Path(bundle) / "Contents" / "MacOS" / "Devin Token Monitor"
        program_args = [str(exe)]
    else:  # dev mode: run module from the project venv
        program_args = [sys.executable, "-m", "devin_token_monitor.gui"]
    workdir = str(Path(__file__).resolve().parent.parent)
    plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>{LOGIN_AGENT_LABEL}</string>
  <key>ProgramArguments</key>
  <array>{''.join(f'<string>{a}</string>' for a in program_args)}</array>
  <key>WorkingDirectory</key><string>{workdir}</string>
  <key>RunAtLoad</key><true/>
  <key>StandardOutPath</key><string>/tmp/devin-token-monitor-gui.log</string>
  <key>StandardErrorPath</key><string>/tmp/devin-token-monitor-gui.log</string>
</dict></plist>"""
    p = _login_plist_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(plist)
    subprocess.run(
        ["launchctl", "bootstrap", f"gui/{os.getuid()}", str(p)],
        capture_output=True,
    )


def _remove_login_item() -> None:
    subprocess.run(
        ["launchctl", "bootout", f"gui/{os.getuid()}/{LOGIN_AGENT_LABEL}"],
        capture_output=True,
    )
    _login_plist_path().unlink(missing_ok=True)


def _fmt_cost(c: float) -> str:
    return f"${c:,.2f}" if c >= 1 else f"${c:.4f}"


# Native-chrome strings (sidebar / menus / tooltips / alerts).  The page
# carries the full dictionary; this mirrors only what AppKit renders.
_L = {
    "zh": {
        "nav_overview": "概览", "nav_models": "模型", "nav_sessions": "会话",
        "nav_requests": "请求", "nav_settings": "设置", "logo_sub": "用量与费用",
        "side_cost": "今日估算费用", "side_loading": "正在读取本地数据",
        "side_reqs": "{n} 次请求 · 本地监控",
        "stat_today": "今日 {v} · {n} 次请求",
        "menu_show": "打开主面板", "menu_quit": "退出", "menu_refresh": "刷新",
        "menu_export": "导出 CSV…", "menu_prices": "编辑价格表 prices.json",
        "menu_login": "登录时启动", "menu_quitapp": "退出 Devin Token Monitor",
        "tip_refresh": "刷新", "tip_export": "导出 CSV", "sel_on": "已选中",
        "alert_suffix": "— ⚠ 超预算",
        "alert_msg": "今日费用 {c} 已超过每日预算 {b}",
        "save_title": "导出用量数据",
    },
    "en": {
        "nav_overview": "Overview", "nav_models": "Models",
        "nav_sessions": "Sessions", "nav_requests": "Requests",
        "nav_settings": "Settings", "logo_sub": "Usage & cost",
        "side_cost": "Today's est. cost", "side_loading": "Reading local data…",
        "side_reqs": "{n} requests · local monitor",
        "stat_today": "Today {v} · {n} requests",
        "menu_show": "Show Window", "menu_quit": "Quit", "menu_refresh": "Refresh",
        "menu_export": "Export CSV…", "menu_prices": "Edit prices.json",
        "menu_login": "Launch at Login", "menu_quitapp": "Quit Devin Token Monitor",
        "tip_refresh": "Refresh", "tip_export": "Export CSV", "sel_on": "selected",
        "alert_suffix": "— ⚠ over budget",
        "alert_msg": "Today's cost {c} exceeded the daily budget {b}",
        "save_title": "Export usage data",
    },
    "ja": {
        "nav_overview": "概要", "nav_models": "モデル", "nav_sessions": "セッション",
        "nav_requests": "リクエスト", "nav_settings": "設定", "logo_sub": "使用量と費用",
        "side_cost": "今日の推定費用", "side_loading": "ローカルデータ読み込み中",
        "side_reqs": "{n} リクエスト · ローカル監視",
        "stat_today": "今日 {v} · {n} リクエスト",
        "menu_show": "パネルを表示", "menu_quit": "終了", "menu_refresh": "更新",
        "menu_export": "CSV 書き出し", "menu_prices": "prices.json を編集",
        "menu_login": "ログイン時に起動", "menu_quitapp": "Devin Token Monitor を終了",
        "tip_refresh": "更新", "tip_export": "CSV 書き出し", "sel_on": "選択中",
        "alert_suffix": "— ⚠ 予算超過",
        "alert_msg": "今日の費用 {c} が毎日の予算 {b} を超えました",
        "save_title": "使用量データを書き出し",
    },
    "ko": {
        "nav_overview": "개요", "nav_models": "모델", "nav_sessions": "세션",
        "nav_requests": "요청", "nav_settings": "설정", "logo_sub": "사용량 및 비용",
        "side_cost": "오늘 예상 비용", "side_loading": "로컬 데이터 읽는 중",
        "side_reqs": "{n}개 요청 · 로컬 모니터",
        "stat_today": "오늘 {v} · {n}개 요청",
        "menu_show": "창 열기", "menu_quit": "종료", "menu_refresh": "새로고침",
        "menu_export": "CSV 보내기", "menu_prices": "prices.json 편집",
        "menu_login": "로그인 시 시작", "menu_quitapp": "Devin Token Monitor 종료",
        "tip_refresh": "새로고침", "tip_export": "CSV 보내기", "sel_on": "선택됨",
        "alert_suffix": "— ⚠ 예산 초과",
        "alert_msg": "오늘 비용 {c}이 일일 예산 {b}을 초과했습니다",
        "save_title": "사용량 데이터 보내기",
    },
    "es": {
        "nav_overview": "Resumen", "nav_models": "Modelos",
        "nav_sessions": "Sesiones", "nav_requests": "Solicitudes",
        "nav_settings": "Ajustes", "logo_sub": "Uso y costo",
        "side_cost": "Costo estimado hoy", "side_loading": "Leyendo datos locales…",
        "side_reqs": "{n} solicitudes · monitor local",
        "stat_today": "Hoy {v} · {n} solicitudes",
        "menu_show": "Mostrar ventana", "menu_quit": "Salir", "menu_refresh": "Actualizar",
        "menu_export": "Exportar CSV…", "menu_prices": "Editar prices.json",
        "menu_login": "Abrir al iniciar sesión", "menu_quitapp": "Salir de Devin Token Monitor",
        "tip_refresh": "Actualizar", "tip_export": "Exportar CSV", "sel_on": "seleccionado",
        "alert_suffix": "— ⚠ sobre presupuesto",
        "alert_msg": "El costo de hoy {c} superó el presupuesto diario {b}",
        "save_title": "Exportar datos de uso",
    },
    "vi": {
        "nav_overview": "Tổng quan", "nav_models": "Mô hình", "nav_sessions": "Phiên",
        "nav_requests": "Yêu cầu", "nav_settings": "Cài đặt", "logo_sub": "Mức dùng & chi phí",
        "side_cost": "Chi phí ước tính hôm nay", "side_loading": "Đang đọc dữ liệu cục bộ…",
        "side_reqs": "{n} yêu cầu · giám sát cục bộ",
        "stat_today": "Hôm nay {v} · {n} yêu cầu",
        "menu_show": "Mở cửa sổ", "menu_quit": "Thoát", "menu_refresh": "Làm mới",
        "menu_export": "Xuất CSV…", "menu_prices": "Sửa prices.json",
        "menu_login": "Khởi động cùng đăng nhập", "menu_quitapp": "Thoát Devin Token Monitor",
        "tip_refresh": "Làm mới", "tip_export": "Xuất CSV", "sel_on": "đã chọn",
        "alert_suffix": "— ⚠ vượt ngân sách",
        "alert_msg": "Chi phí hôm nay {c} đã vượt ngân sách ngày {b}",
        "save_title": "Xuất dữ liệu sử dụng",
    },
}
_NAV_KEYS = ("nav_overview", "nav_insights", "nav_models", "nav_sessions", "nav_requests", "nav_settings")
_NATIVE_EXTRA = {
    "zh": {"nav_insights": "分析"}, "en": {"nav_insights": "Insights"},
    "ja": {"nav_insights": "分析"}, "ko": {"nav_insights": "분석"},
    "es": {"nav_insights": "Análisis"}, "vi": {"nav_insights": "Phân tích"},
}


def _nlf(lang: str, key: str, **kw) -> str:
    s = (
        _L.get(lang, _L["en"]).get(key)
        or _NATIVE_EXTRA.get(lang, {}).get(key)
        or _L["en"].get(key)
        or key
    )
    for k, v in kw.items():
        s = s.replace("{" + k + "}", str(v))
    return s


def _guarded(fn):
    """Every ObjC-invoked entry point: a Python exception that escapes into
    the ObjC runtime becomes an NSException and aborts the process.  Log and
    swallow instead — a monitor that dies silently is worse than a missed tick."""
    @functools.wraps(fn)
    def wrapper(self, *args):
        try:
            return fn(self, *args)
        except Exception as e:
            print(f"{fn.__name__} error: {e}")
    return wrapper


class AppDelegate(NSObject):
    @_guarded
    def applicationDidFinishLaunching_(self, _note):
        self.agg = UsageAggregator(PriceTable.load())
        self.agg.meta = {
            "db_path": str(db_path()),
            "prices_path": str(default_prices_path()),
            "version": __version__,
            "login_item": _login_item_installed(),
        }
        self._alerted_day = None
        self._last_poll_error = None
        self._poll_lock = threading.Lock()
        self._lang = self.agg.prices.language
        self._theme = str(self.agg.prices.settings.get("theme", "system") or "system")
        try:
            self.agg.poll()
        except Exception as e:
            self._last_poll_error = str(e)
            print(f"warning: {e}")

        # ---- main window: opaque, Apple-Settings style ----
        # Standard opaque window; the page itself is solid white. Traffic
        # lights float over the sidebar (full-size content view).
        style = (
            NSWindowStyleMaskTitled
            | NSWindowStyleMaskClosable
            | NSWindowStyleMaskMiniaturizable
            | NSWindowStyleMaskResizable
            | NSWindowStyleMaskFullSizeContentView
        )
        rect = NSMakeRect(0, 0, 950, 720)
        self.window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            rect, style, NSBackingStoreBuffered, False
        )
        self.window.setTitle_("Devin Token Monitor")
        self.window.setMinSize_(NSMakeSize(860, 560))
        self.window.setTitlebarAppearsTransparent_(True)
        self.window.setTitleVisibility_(NSWindowTitleHidden)
        self.window.setMovableByWindowBackground_(True)
        # disallow automatic window tabbing — otherwise the window can get
        # absorbed into a tab group and collapse to a stub frame
        try:
            self.window.setTabbingMode_(2)  # NSWindowTabbingModeDisallowed
        except Exception:
            pass
        try:
            self.window.setRestorable_(False)
        except Exception:
            pass
        self.window.setFrame_display_(rect, True)
        self.window.center()
        self.window.makeKeyAndOrderFront_(None)
        NSApp.activateIgnoringOtherApps_(True)

        # ---- status bar item ----
        self.status_item = (
            NSStatusBar.systemStatusBar().statusItemWithLength_(
                NSVariableStatusItemLength
            )
        )
        # Cache the button once at startup. On macOS 27 the system
        # re-parents status items into private NSSceneStatusItem objects
        # *after* launch; any later attribute access on the status item —
        # including the implicit sender object marshalled into a Python
        # menu action — makes PyObjC build a proxy metaclass for that
        # private class and crashes in libobjc (pointer-auth trap).  So:
        # (1) only ever touch this cached button afterwards, never the
        # item itself; (2) every menu action below targets a *native*
        # object with a *native* selector — AppKit dispatches the action
        # in pure ObjC and the status-item sender never enters Python.
        self._status_btn = self.status_item.button()
        self._status_btn.setTitle_("$—")
        sm = NSMenu.alloc().init()
        self._stat_today = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            _nlf(self._lang, "stat_today", v="—", n=0), None, ""
        )
        self._stat_today.setEnabled_(False)
        sm.addItem_(self._stat_today)
        sm.addItem_(NSMenuItem.separatorItem())
        # native target+action: shows the window without Python marshalling
        self._m_show = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            self._nl("menu_show"), "makeKeyAndOrderFront:", ""
        )
        self._m_show.setTarget_(self.window)
        sm.addItem_(self._m_show)
        sm.addItem_(NSMenuItem.separatorItem())
        self._m_quit = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            self._nl("menu_quit"), "terminate:", "q"
        )
        sm.addItem_(self._m_quit)
        self.status_item.setMenu_(sm)
        # makeKeyAndOrderFront: alone doesn't activate the app; bring it
        # forward once the window becomes key.  The notification object
        # passed to the handler is a public NSNotification — safe to wrap.
        try:
            from Foundation import NSNotificationCenter

            NSNotificationCenter.defaultCenter().addObserver_selector_name_object_(
                self, "windowKey:", "NSWindowDidBecomeKeyNotification",
                self.window,
            )
        except Exception:
            pass

        config = WKWebViewConfiguration.alloc().init()
        config.userContentController().addScriptMessageHandler_name_(
            self, "dtm"
        )
        self.webview = WKWebView.alloc().initWithFrame_configuration_(
            rect, config
        )
        self.webview.setNavigationDelegate_(self)
        self._build_native_shell(rect)
        self.webview.loadHTMLString_baseURL_(
            PAGE.replace('<body>', '<body class="native-shell">'), None
        )

        # last-line defence: if anything collapsed the frame during setup,
        # put it back to a sane size while it's still on screen
        f = self.window.frame()
        if f.size.width < 600 or f.size.height < 400:
            self.window.setFrame_display_(rect, True)
            self.window.center()

        # macOS may restore a degenerate saved frame *after* orderFront —
        # re-assert the default size once, shortly after launch
        NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            0.6, self, "fixFrame:", None, False
        )

        NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            POLL_SECONDS, self, "tick:", None, True
        )

    @objc.python_method
    def _glass(self, frame, radius):
        glass_class = getattr(AK, "NSGlassEffectView", None)
        glass = (glass_class or AK.NSVisualEffectView).alloc().initWithFrame_(frame)
        content = AK.NSView.alloc().initWithFrame_(glass.bounds())
        content.setAutoresizingMask_(AK.NSViewWidthSizable | AK.NSViewHeightSizable)
        if glass_class:
            glass.setStyle_(AK.NSGlassEffectViewStyleRegular)
            glass.setCornerRadius_(radius)
            glass.setContentView_(content)
        else:
            glass.setMaterial_(AK.NSVisualEffectMaterialSidebar)
            glass.setBlendingMode_(AK.NSVisualEffectBlendingModeBehindWindow)
            glass.setWantsLayer_(True)
            glass.layer().setCornerRadius_(radius)
            glass.layer().setMasksToBounds_(True)
            glass.addSubview_(content)
        return glass, content

    @objc.python_method
    def _label(self, parent, text, frame, size, weight, secondary=False):
        label = AK.NSTextField.labelWithString_(text)
        label.setFrame_(frame)
        label.setFont_(AK.NSFont.systemFontOfSize_weight_(size, weight))
        label.setTextColor_(
            AK.NSColor.secondaryLabelColor() if secondary else AK.NSColor.labelColor()
        )
        parent.addSubview_(label)
        return label

    @objc.python_method
    def _build_native_shell(self, rect):
        width, height = rect.size.width, rect.size.height
        self.shell = AK.NSView.alloc().initWithFrame_(rect)
        self.window.setContentView_(self.shell)
        self.window.setOpaque_(True)
        self.window.setBackgroundColor_(AK.NSColor.windowBackgroundColor())
        self.webview.setFrame_(self.shell.bounds())
        self.webview.setAutoresizingMask_(AK.NSViewWidthSizable | AK.NSViewHeightSizable)
        self.shell.addSubview_(self.webview)
        self.sidebar, content = self._glass(NSMakeRect(10, 10, 210, height - 58), 22)
        self.sidebar.setAutoresizingMask_(AK.NSViewHeightSizable)
        self.shell.addSubview_(self.sidebar)
        top = height - 58
        title = self._label(content, "Devin Token", NSMakeRect(20, top - 58, 172, 26),
                            19, AK.NSFontWeightSemibold)
        self._subtitle = self._label(content, self._nl("logo_sub"),
                                     NSMakeRect(20, top - 79, 172, 20),
                                     11, AK.NSFontWeightRegular, True)
        subtitle = self._subtitle
        for label in (title, subtitle):
            label.setAutoresizingMask_(AK.NSViewMinYMargin)
        self._views = ("overview", "insights", "models", "sessions", "requests", "settings")
        self._nav_buttons = []
        self.selection = AK.NSBox.alloc().initWithFrame_(NSMakeRect(10, top - 142, 190, 38))
        self.selection.setBoxType_(AK.NSBoxCustom)
        self.selection.setBorderType_(AK.NSNoBorder)
        self.selection.setTitlePosition_(AK.NSNoTitle)
        self.selection.setCornerRadius_(12)
        self._native_accent = AK.NSColor.controlAccentColor()
        self._apply_native_theme(self._theme)
        self.selection.setFillColor_(self._native_accent.colorWithAlphaComponent_(0.14))
        self.selection.setAutoresizingMask_(AK.NSViewMinYMargin)
        content.addSubview_(self.selection)
        items = (("nav_overview", "chart.bar"), ("nav_insights", "chart.xyaxis.line"),
                 ("nav_models", "square.stack"), ("nav_sessions", "bubble.left"),
                 ("nav_requests", "list.bullet"), ("nav_settings", "slider.horizontal.3"))
        for index, (key, symbol) in enumerate(items):
            title = self._nl(key)
            button = AK.NSButton.alloc().initWithFrame_(NSMakeRect(16, top - 142 - index * 46, 178, 38))
            button.setTitle_("  " + title)
            button.setFont_(AK.NSFont.systemFontOfSize_weight_(13, AK.NSFontWeightRegular))
            button.setBordered_(False)
            button.setAlignment_(AK.NSTextAlignmentLeft)
            image = AK.NSImage.imageWithSystemSymbolName_accessibilityDescription_(symbol, title)
            button.setImage_(image.imageWithSymbolConfiguration_(
                AK.NSImageSymbolConfiguration.configurationWithPointSize_weight_(18, AK.NSFontWeightRegular)
            ))
            button.setImagePosition_(AK.NSImageLeft)
            button.setTag_(index)
            button.setTarget_(self)
            button.setAction_("navigate:")
            button.setAccessibilityLabel_(title)
            button.setAutoresizingMask_(AK.NSViewMinYMargin)
            content.addSubview_(button)
            self._nav_buttons.append(button)
        self._side_lbl = self._label(content, self._nl("side_cost"),
                                     NSMakeRect(20, 82, 170, 18),
                                     11, AK.NSFontWeightRegular, True)
        self.side_cost = self._label(content, "—", NSMakeRect(20, 43, 170, 36),
                                     26, AK.NSFontWeightSemibold)
        self.side_requests = self._label(content, self._nl("side_loading"),
                                         NSMakeRect(20, 22, 170, 18),
                                         11, AK.NSFontWeightRegular, True)
        self.toolbar, actions = self._glass(NSMakeRect(width - 118, height - 62, 88, 36), 18)
        self.toolbar.setAutoresizingMask_(AK.NSViewMinXMargin | AK.NSViewMinYMargin)
        self.shell.addSubview_(self.toolbar)
        self._tb_btns = []
        for index, (key, symbol, action) in enumerate((
            ("tip_refresh", "arrow.clockwise", "refresh:"),
            ("tip_export", "square.and.arrow.up", "exportCsv:"),
        )):
            title = self._nl(key)
            button = AK.NSButton.alloc().initWithFrame_(NSMakeRect(4 + index * 40, 2, 40, 32))
            button.setBordered_(False)
            button.setImage_(AK.NSImage.imageWithSystemSymbolName_accessibilityDescription_(symbol, title))
            button.setImagePosition_(AK.NSImageOnly)
            button.setToolTip_(title)
            button.setAccessibilityLabel_(title)
            button.setTarget_(self)
            button.setAction_(action)
            actions.addSubview_(button)
            self._tb_btns.append(button)
        self._select_navigation("overview")

    @objc.python_method
    def _nl(self, key):
        return _nlf(self._lang, key)

    @objc.python_method
    def _apply_lang(self):
        """Re-render every native-chrome string after a language change."""
        nl = self._nl
        self._subtitle.setStringValue_(nl("logo_sub"))
        self._side_lbl.setStringValue_(nl("side_cost"))
        for i, button in enumerate(self._nav_buttons):
            lbl = nl(_NAV_KEYS[i])
            button.setTitle_("  " + lbl)
            button.setAccessibilityLabel_(lbl)
        for i, key in enumerate(("tip_refresh", "tip_export")):
            self._tb_btns[i].setToolTip_(nl(key))
            self._tb_btns[i].setAccessibilityLabel_(nl(key))
        self._m_show.setTitle_(nl("menu_show"))
        self._m_quit.setTitle_(nl("menu_quit"))
        am = getattr(self, "_app_menu", None)
        if am:
            for key, item in am.items():
                item.setTitle_(nl(key))
        self._select_navigation(getattr(self, "_current_view", "overview"))

    @objc.python_method
    def _apply_native_theme(self, theme):
        accents = {
            "midnight": "#8ca8ff", "graphite": "#b7c3cc",
            "paper": "#96613f", "ocean": "#59bce9", "forest": "#88cb96",
        }
        color = accents.get(theme)
        if color:
            rgb = tuple(int(color[i:i + 2], 16) / 255 for i in (1, 3, 5))
            self._native_accent = AK.NSColor.colorWithSRGBRed_green_blue_alpha_(*rgb, 1)
        else:
            self._native_accent = AK.NSColor.controlAccentColor()
        if hasattr(self, "selection"):
            self.selection.setFillColor_(self._native_accent.colorWithAlphaComponent_(0.14))
        if getattr(self, "_nav_buttons", None):
            self._select_navigation(getattr(self, "_current_view", "overview"))

    @_guarded
    def windowKey_(self, _note):
        # status-menu "Show Window" is a native action (no Python sender
        # marshalling); compensate for the lost activation here
        NSApp.activateIgnoringOtherApps_(True)
        if hasattr(self, "webview"):
            self.push()

    @objc.python_method
    def _select_navigation(self, view):
        if view not in self._views:
            return
        index = self._views.index(view)
        self._current_view = view
        frame = self._nav_buttons[index].frame()
        self.selection.setFrameOrigin_((10, frame.origin.y))
        for i, button in enumerate(self._nav_buttons):
            button.setContentTintColor_(self._native_accent if i == index
                                        else AK.NSColor.labelColor())
            button.setAccessibilityValue_(self._nl("sel_on") if i == index else "")

    @_guarded
    def navigate_(self, sender):
        tag = sender.tag()
        if not (0 <= tag < len(self._views)):
            return
        view = self._views[tag]
        self._select_navigation(view)
        self.webview.evaluateJavaScript_completionHandler_(
            "navigateTo(%s)" % json.dumps(view), None
        )

    @_guarded
    def applicationShouldTerminateAfterLastWindowClosed_(self, _app):
        # stay alive in the status bar; reopen via its menu or dock icon
        return False

    @_guarded
    def applicationShouldHandleReopen_hasVisibleWindows_(self, _app, flag):
        if not flag:
            self.showWindow_(None)
        return True

    # WKNavigationDelegate: push once the page (and `update`) is ready
    @_guarded
    def webView_didFinishNavigation_(self, _wv, _nav):
        self.push()

    # WKScriptMessageHandler: page actions
    def userContentController_didReceiveScriptMessage_(self, _ucc, msg):
        try:
            self._handle_page_message(msg)
        except Exception as e:
            # never let a page action abort the app
            print(f"bridge action error: {e}")

    @objc.python_method
    def _save_settings(self, patch):
        path = self.agg.prices.update_settings(patch)
        self.agg.prices = PriceTable.load()
        self.agg.meta["prices_path"] = str(path)

    def _handle_page_message(self, msg):
        body = msg.body()
        action = body.objectForKey_("action") if body else None
        if action == "jserr":
            print(f"PAGE JS ERROR: {body.objectForKey_('msg')}")
        elif action == "navigate":
            self._select_navigation(str(body.objectForKey_("view") or ""))
        elif action == "refresh":
            self.refresh_(None)
        elif action == "export":
            self.exportCsv_(None)
        elif action == "editPrices":
            self.editPrices_(None)
        elif action == "setBudget":
            v = body.objectForKey_("value") or 0
            try:
                self._save_settings({"daily_budget": float(v)})
            except Exception as e:
                print(f"setBudget error: {e}")
            self.push()
        elif action == "setLanguage":
            v = str(body.objectForKey_("value") or "zh")
            try:
                self._save_settings({"language": v})
            except Exception as e:
                print(f"setLanguage error: {e}")
            self.push()
        elif action == "setTheme":
            v = str(body.objectForKey_("value") or "system")
            try:
                self._save_settings({"theme": v})
            except Exception as e:
                print(f"setTheme error: {e}")
            self.push()
        elif action == "getBody":
            # lazy-load one request's reply body off the main thread, then
            # deliver back into the page
            rid = str(body.objectForKey_("rid") or "")
            mid = str(body.objectForKey_("mid") or "")
            threading.Thread(
                target=self._fetch_body, args=(rid, mid), daemon=True
            ).start()
        elif action == "drag":
            # track by polling mouse position — never touches the event
            # that triggered the message (that path crashed before).
            # Ignore repeat mousedowns while a drag timer is already live,
            # otherwise stacked timers keep scheduling ObjC objects.
            if getattr(self, "_drag_timer", None) is not None:
                return
            self._drag_origin = self.window.frame().origin
            self._drag_mouse = NSEvent.mouseLocation()
            self._drag_timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
                0.008, self, "dragMove:", None, True
            )
        elif action == "toggleLoginItem":
            want_on = bool(body.objectForKey_("on"))
            if want_on and not _login_item_installed():
                _write_login_item()
            elif not want_on and _login_item_installed():
                _remove_login_item()
            self.agg.meta["login_item"] = _login_item_installed()
            self.push()

    @_guarded
    def fixFrame_(self, _timer):
        f = self.window.frame()
        if f.size.width < 600 or f.size.height < 400:
            self.window.setFrame_display_(NSMakeRect(200, 120, 950, 720), True)
            self.window.center()

    # ---- lazy request body ------------------------------------------------

    def _fetch_body(self, rid, mid):
        try:
            text = self.agg.request_body(rid, mid)
        except Exception as e:
            print(f"fetch body error: {e}")
            text = ""
        js = "showBody(%s,%s)" % (json.dumps(rid or mid), json.dumps(text))
        try:
            self.performSelectorOnMainThread_withObject_waitUntilDone_(
                "evalJS:", js, False
            )
        except Exception as e:
            print(f"deliver body error: {e}")

    @_guarded
    def evalJS_(self, js):
        self.webview.evaluateJavaScript_completionHandler_(js, None)

    # ---- window drag -----------------------------------------------------

    @_guarded
    def dragMove_(self, timer):
        if NSEvent.pressedMouseButtons() == 0 or not hasattr(self, "_drag_mouse"):
            timer.invalidate()
            self._drag_timer = None
            return
        m = NSEvent.mouseLocation()
        d = self._drag_mouse
        o = self._drag_origin
        f = self.window.frame()
        f.origin.x = o.x + (m.x - d.x)
        f.origin.y = o.y + (m.y - d.y)
        self.window.setFrameOrigin_(f.origin)

    # ---- polling ---------------------------------------------------------

    @_guarded
    def tick_(self, _timer):
        f = self.window.frame()
        if f.size.width < 600 or f.size.height < 400:
            self.window.setFrame_display_(
                NSMakeRect(200, 120, 950, 720), True
            )
            self.window.center()
        if not self._poll_lock.acquire(blocking=False):
            return
        try:
            threading.Thread(target=self._poll_and_push, daemon=True).start()
        except Exception:
            self._poll_lock.release()
            raise

    def _poll_and_push(self):
        try:
            try:
                self.agg.poll()
                self._last_poll_error = None
            except Exception as e:
                message = str(e)
                if message != self._last_poll_error:
                    print(f"poll error: {message}")
                self._last_poll_error = message
            try:
                self.performSelectorOnMainThread_withObject_waitUntilDone_(
                    "push", None, False
                )
            except Exception as e:
                print(f"dispatch push error: {e}")
        finally:
            self._poll_lock.release()

    @_guarded
    def push(self):
        full = self.window.isVisible() and not self.window.isMiniaturized()
        snap = self.agg.snapshot() if full else self.agg.status_summary()
        self._maybe_alert(snap)
        lang = self.agg.prices.language
        if lang != self._lang:
            self._lang = lang
            self._apply_lang()
        theme = str((snap.get("settings") or {}).get("theme", "system") or "system")
        if theme != self._theme:
            self._theme = theme
            self._apply_native_theme(theme)
        today = snap.get("today") or {}
        cost = today.get("cost") or 0
        title = _fmt_cost(cost)
        # only touch the cached status-bar button when the text actually
        # changes — each access re-verifies its ObjC class, and we want as
        # few such calls as possible (see launch-time comment above)
        if title != getattr(self, "_status_title", None):
            self._status_title = title
            self._status_btn.setTitle_(title)
        self.side_cost.setStringValue_(title)
        self.side_requests.setStringValue_(
            _nlf(self._lang, "side_reqs", n=f"{today.get('requests', 0):,}")
        )
        self._stat_today.setTitle_(
            _nlf(self._lang, "stat_today", v=title, n=today.get("requests", 0))
        )
        if full:
            self.webview.evaluateJavaScript_completionHandler_(
                f"update({json.dumps(snap)})", None
            )

    # ---- budget alert ----------------------------------------------------

    def _maybe_alert(self, snap):
        budget = snap.get("settings", {}).get("daily_budget") or 0
        cost = (snap.get("today") or {}).get("cost") or 0
        today = date.today().isoformat()
        if budget and cost > budget and self._alerted_day != today:
            self._alerted_day = today
            self.window.setTitle_(
                "Devin Token Monitor " + self._nl("alert_suffix")
            )
            msg = _nlf(
                self._lang, "alert_msg",
                c=f"${cost:.2f}", b=f"${budget:.2f}"
            ).replace('"', "'")
            subprocess.Popen(
                [
                    "osascript",
                    "-e",
                    'display notification '
                    f'"{msg}" '
                    'with title "Devin Token Monitor" sound name "Basso"',
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

    # ---- menu actions ----------------------------------------------------

    @_guarded
    def showWindow_(self, _sender):
        f = self.window.frame()
        # a stale/restored degenerate frame (tiny or fully off-screen)
        # leaves the user with an invisible window — snap back to default
        if f.size.width < 600 or f.size.height < 400:
            self.window.setFrame_display_(NSMakeRect(200, 120, 950, 720), True)
        self.window.makeKeyAndOrderFront_(None)
        NSApp.activateIgnoringOtherApps_(True)

    @_guarded
    def refresh_(self, _sender):
        self.agg.prices = PriceTable.load()
        self.agg.meta["prices_path"] = str(default_prices_path())
        self.tick_(None)

    @_guarded
    def editPrices_(self, _sender):
        path = editable_prices_path()
        self.agg.meta["prices_path"] = str(path)
        subprocess.Popen(["open", "-t", str(path)])
        self.push()

    @_guarded
    def toggleLoginItem_(self, sender):
        # App-menu item action (the page uses the "toggleLoginItem" bridge
        # action instead).  Missing this method = unrecognized selector =
        # crash when the menu item is clicked.
        if _login_item_installed():
            _remove_login_item()
        else:
            _write_login_item()
        installed = _login_item_installed()
        if sender is not None:
            sender.setState_(1 if installed else 0)
        if hasattr(self, "agg"):
            self.agg.meta["login_item"] = installed
            self.push()

    @_guarded
    def exportCsv_(self, _sender):
        panel = NSSavePanel.savePanel()
        panel.setTitle_(self._nl("save_title"))
        panel.setNameFieldStringValue_(
            f"devin-usage-{date.today().isoformat()}.zip"
        )
        panel.setAllowedFileTypes_(["zip"])
        if panel.runModal() != NSModalResponseOK:
            return
        path = panel.URL().path()
        data = export_all(self.agg.snapshot())
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
            for name, text in data.items():
                z.writestr(f"{name}.csv", text)


def _build_menu(delegate):
    # main-menu actions target the delegate — the sender is always the
    # public NSMenuItem here, so PyObjC marshalling is safe (the
    # NSSceneStatusItem trap only affects the *status-bar* menu)
    lang = delegate._lang
    menubar = NSMenu.alloc().init()
    app_item = NSMenuItem.alloc().init()
    menubar.addItem_(app_item)
    menu = NSMenu.alloc().initWithTitle_("Devin Token Monitor")
    delegate._app_menu = {}

    entries = [
        ("menu_refresh", "refresh:", "r", True),
        ("menu_export", "exportCsv:", "e", True),
        ("menu_prices", "editPrices:", ",", True),
        (None, None, None, None),
        ("menu_login", "toggleLoginItem:", "l", True),
        (None, None, None, None),
        ("menu_quitapp", "terminate:", "q", False),
    ]
    for keyname, action, key, targeted in entries:
        if keyname is None:
            menu.addItem_(NSMenuItem.separatorItem())
            continue
        item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            _nlf(lang, keyname), action, key
        )
        if targeted:
            item.setTarget_(delegate)
        if action == "toggleLoginItem:":
            item.setState_(1 if _login_item_installed() else 0)
        menu.addItem_(item)
        delegate._app_menu[keyname] = item

    app_item.setSubmenu_(menu)
    NSApp.setMainMenu_(menubar)


def main() -> int:
    global _delegate
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyRegular)
    _delegate = AppDelegate.alloc().init()
    _delegate._lang = PriceTable.load().language
    app.setDelegate_(_delegate)
    _build_menu(_delegate)
    app.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
