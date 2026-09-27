"""CSV export of usage snapshots — shared by the web API and the app."""

from __future__ import annotations

import csv
import io

_KINDS = ("requests", "sessions", "daily", "models")


def export_csv(snapshot: dict, what: str) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    if what == "requests":
        w.writerow(
            ["time", "model", "session", "input", "output", "cache_read",
             "cache_creation", "ttft_ms", "total_ms", "tok_per_s",
             "cost_usd", "request_id"]
        )
        for r in snapshot.get("requests", []):
            w.writerow(
                [r["ts"], r["model"], r["session_title"], r["input"],
                 r["output"], r["cache_read"], r["cache_creation"],
                 r.get("ttft_ms"), r.get("total_ms"), r.get("tok_per_s"),
                 r.get("cost"), r.get("request_id")]
            )
    elif what == "sessions":
        w.writerow(
            ["last_activity", "title", "directory", "models", "requests",
             "input", "output", "cache_read", "total", "cost_usd"]
        )
        for s in snapshot.get("sessions", []):
            w.writerow(
                [s["last_ts"], s["title"], s["dir"], " ".join(s["models"]),
                 s["requests"], s["input"], s["output"], s["cache_read"],
                 s["total"], s["cost"]]
            )
    elif what == "daily":
        w.writerow(
            ["day", "requests", "input", "output", "cache_read",
             "cache_creation", "total", "cost_usd"]
        )
        for d in snapshot.get("by_day", []):
            w.writerow(
                [d["day"], d["requests"], d["input"], d["output"],
                 d["cache_read"], d["cache_creation"], d["total"], d["cost"]]
            )
    elif what == "models":
        w.writerow(
            ["model", "price_in", "price_out", "price_cache_read",
             "price_cache_creation", "requests", "input", "output",
             "cache_read", "total", "cost_usd"]
        )
        for m in snapshot.get("by_model", []):
            p = m["price"]
            w.writerow(
                [m["model"], p["input"], p["output"], p["cache_read"],
                 p["cache_creation"], m["requests"], m["input"], m["output"],
                 m["cache_read"], m["total"], m["cost"]]
            )
    else:
        raise ValueError(f"unknown export kind: {what!r} (one of {_KINDS})")
    return buf.getvalue()


def export_all(snapshot: dict) -> dict[str, str]:
    return {k: export_csv(snapshot, k) for k in _KINDS}
