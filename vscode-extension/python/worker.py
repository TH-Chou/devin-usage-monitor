from __future__ import annotations

import base64
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from devin_token_monitor import __version__
from devin_token_monitor.aggregator import UsageAggregator
from devin_token_monitor.exporter import export_zip
from devin_token_monitor.db import db_path
from devin_token_monitor.pricing import PriceTable, default_prices_path, editable_prices_path

aggregator: UsageAggregator | None = None


def get_aggregator() -> UsageAggregator:
    global aggregator
    if aggregator is None:
        prices = PriceTable.load()
        aggregator = UsageAggregator(prices)
        aggregator.meta = {
            "db_path": str(db_path()),
            "version": __version__,
            "prices_path": str(default_prices_path()),
        }
    return aggregator


def handle(message: dict) -> dict:
    action = message.get("action")
    if action in ("initialize", "poll", "refresh"):
        agg = get_aggregator()
        if action == "refresh":
            agg.prices = PriceTable.load()
        error = None
        try:
            agg.poll(rebuild=action == "refresh")
        except Exception as exc:
            error = str(exc)
        include_snapshot = bool(message.get("include_snapshot", True))
        result = {"snapshot" if include_snapshot else "summary":
                  agg.snapshot() if include_snapshot else agg.status_summary()}
        if error:
            result["error"] = error
        return result
    if action == "usageReport":
        filters = (str(message.get(key) or "") for key in ("start", "end", "model"))
        return {"report": get_aggregator().usage_report(*filters)}
    if action == "settings":
        agg = get_aggregator()
        patch = message.get("settings") or {}
        path = agg.prices.update_settings(patch)
        agg.prices = PriceTable.load()
        agg.meta["prices_path"] = str(path)
        return {"snapshot": agg.snapshot()}
    if action == "body":
        agg = get_aggregator()
        return {
            "body": agg.request_body(
                str(message.get("request_id") or ""),
                str(message.get("message_id") or ""),
            )
        }
    if action == "pricesPath":
        return {"path": str(editable_prices_path())}
    if action == "export":
        agg = get_aggregator()
        data = export_zip(agg.snapshot())
        return {"data": base64.b64encode(data).decode("ascii")}
    raise ValueError(f"unsupported action: {action!r}")


def main() -> int:
    if sys.version_info < (3, 10):
        print("Python 3.10 or newer is required.", file=sys.stderr, flush=True)
        return 2
    # Node's readline stream decodes child-process stdout as UTF-8. Windows
    # otherwise uses the active console code page for redirected stdio.
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    sys.stderr.reconfigure(encoding="utf-8")
    for line in sys.stdin:
        request_id = None
        try:
            request = json.loads(line)
            if not isinstance(request, dict):
                raise ValueError("Expected a JSON object")
            request_id = request.get("id")
            result = handle(request)
            encoded = json.dumps({"id": request_id, "ok": True, "result": result},
                                 ensure_ascii=False, allow_nan=False)
        except Exception as exc:
            encoded = json.dumps({"id": request_id, "ok": False, "error": str(exc)})
        try:
            sys.stdout.write(encoded + "\n")
            sys.stdout.flush()
        except (BrokenPipeError, OSError):
            return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
