from __future__ import annotations

import base64
import io
import json
import os
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from devin_token_monitor.aggregator import UsageAggregator
from devin_token_monitor.exporter import export_all
from devin_token_monitor.db import db_path
from devin_token_monitor.pricing import PriceTable, default_prices_path

aggregator: UsageAggregator | None = None


def get_aggregator() -> UsageAggregator:
    global aggregator
    if aggregator is None:
        prices = PriceTable.load()
        aggregator = UsageAggregator(prices)
        aggregator.meta = {
            "db_path": str(db_path()),
            "prices_path": str(default_prices_path()),
        }
    return aggregator


def handle(message: dict) -> dict:
    action = message.get("action")
    if action in ("initialize", "poll", "refresh"):
        agg = get_aggregator()
        if action == "refresh":
            agg.prices = PriceTable.load()
        agg.poll()
        return {"snapshot": agg.snapshot()}
    if action == "settings":
        agg = get_aggregator()
        patch = message.get("settings") or {}
        agg.prices.update_settings(patch)
        agg.prices = PriceTable.load()
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
        return {"path": str(default_prices_path())}
    if action == "export":
        agg = get_aggregator()
        files = export_all(agg.snapshot())
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
            for name, contents in files.items():
                archive.writestr(f"{name}.csv", contents)
        return {"data": base64.b64encode(stream.getvalue()).decode("ascii")}
    raise ValueError(f"unsupported action: {action!r}")


def main() -> int:
    if sys.version_info < (3, 10):
        print("Python 3.10 or newer is required.", file=sys.stderr, flush=True)
        return 2
    for line in sys.stdin:
        request = {}
        try:
            request = json.loads(line)
            result = handle(request)
            response = {"id": request.get("id"), "ok": True, "result": result}
        except Exception as exc:
            response = {
                "id": request.get("id"),
                "ok": False,
                "error": str(exc),
            }
        try:
            sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
            sys.stdout.flush()
        except (BrokenPipeError, OSError):
            return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
