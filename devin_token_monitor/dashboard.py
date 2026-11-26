"""Assemble the shared, self-contained dashboard for WebKit, HTTP and the VSIX."""

import os
import sys
from pathlib import Path

_ASSETS = Path(__file__).with_name("dashboard_ui")
if not _ASSETS.is_dir() and getattr(sys, "frozen", False):
    resources = os.environ.get("RESOURCEPATH") or Path(sys.executable).parents[1] / "Resources"
    _ASSETS = Path(resources) / "dashboard_ui"

_SCRIPTS = (
    "core.js", "locales.js", "navigation.js", "charts.js", "records.js",
    "overview.js", "report.js", "app.js",
)


def _asset(name: str) -> str:
    return (_ASSETS / name).read_text(encoding="utf-8")


PAGE = (_asset("index.html")
        .replace("<!-- dashboard-brand -->", _asset("monitor-mark.svg").strip())
        .replace("<!-- dashboard-style -->", _asset("styles.css"))
        .replace("<!-- dashboard-script -->", "\n".join(_asset(name) for name in _SCRIPTS)))
