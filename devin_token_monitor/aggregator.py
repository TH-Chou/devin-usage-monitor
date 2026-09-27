"""Incremental aggregation of token usage rows.

The aggregator keeps a ``row_id`` watermark over ``message_nodes`` and
folds each inference request into running totals by model, session, and
local calendar day.  A full pass over the database takes well under a
second, so correctness never depends on persisted state.
"""

from __future__ import annotations

import calendar
import threading
from collections import deque
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Iterable

from .db import (
    UsageRow,
    connect,
    fetch_message_body,
    fetch_usage_rows,
)
from .pricing import PriceTable

RECENT_LIMIT = 5000  # deduped request rows kept for the frontend


@dataclass
class UsageStats:
    requests: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0
    speed_sum: float = 0.0   # sum of per-request tokens/sec samples
    speed_n: int = 0
    ttft_sum: float = 0.0    # sum of per-request first-token latency (ms)
    ttft_n: int = 0

    def add(self, row: UsageRow) -> None:
        self.requests += 1
        self.input_tokens += row.input_tokens
        self.output_tokens += row.output_tokens
        self.cache_read_tokens += row.cache_read_tokens
        self.cache_creation_tokens += row.cache_creation_tokens
        if row.tokens_per_sec is not None:
            self.speed_sum += row.tokens_per_sec
            self.speed_n += 1
        if row.ttft_ms is not None:
            self.ttft_sum += row.ttft_ms
            self.ttft_n += 1

    @property
    def avg_speed(self) -> float | None:
        return self.speed_sum / self.speed_n if self.speed_n else None

    @property
    def avg_ttft_ms(self) -> float | None:
        return self.ttft_sum / self.ttft_n if self.ttft_n else None

    @property
    def hit_rate(self) -> float | None:
        denom = self.input_tokens + self.cache_read_tokens
        return self.cache_read_tokens / denom if denom else None

    @property
    def total_tokens(self) -> int:
        return (
            self.input_tokens
            + self.output_tokens
            + self.cache_read_tokens
            + self.cache_creation_tokens
        )


@dataclass
class SessionBucket:
    title: str = "(untitled)"
    working_directory: str = ""
    last_ts: datetime = datetime.min.replace(tzinfo=timezone.utc)
    by_model: dict[str, UsageStats] = field(default_factory=dict)

    @property
    def stats(self) -> UsageStats:
        total = UsageStats()
        for s in self.by_model.values():
            total.requests += s.requests
            total.input_tokens += s.input_tokens
            total.output_tokens += s.output_tokens
            total.cache_read_tokens += s.cache_read_tokens
            total.cache_creation_tokens += s.cache_creation_tokens
        return total

    def cost(self, prices: PriceTable) -> float:
        total = 0.0
        for model, s in self.by_model.items():
            p = prices.price_for(model)
            total += p.cost(
                s.input_tokens,
                s.output_tokens,
                s.cache_read_tokens,
                s.cache_creation_tokens,
            )
        return total


class UsageAggregator:
    def __init__(self, prices: PriceTable):
        self.prices = prices
        self.watermark = 0
        self.total = UsageStats()
        self.by_model: dict[str, UsageStats] = {}
        self.by_day: dict[str, UsageStats] = {}  # local-date string -> stats
        self.by_day_model: dict[str, dict[str, UsageStats]] = {}
        self.by_hour: dict[str, UsageStats] = {}  # 'YYYY-MM-DDTHH' -> stats
        self.by_hour_model: dict[str, dict[str, UsageStats]] = {}
        self.by_weekhour: dict[str, UsageStats] = {}  # "dow-hour" -> stats
        self.by_weekhour_model: dict[str, dict[str, UsageStats]] = {}
        self.by_session: dict[str, SessionBucket] = {}
        self.new_requests = 0  # rows ingested by the most recent poll
        self.recent: deque[dict] = deque(maxlen=RECENT_LIMIT)
        self.lock = threading.RLock()
        self.meta: dict = {}  # caller-provided info (db path, version, …)
        # sessions.db stores some messages under two node_ids (tree branch
        # copies) — same request/message id, same metrics. Dedupe so each
        # inference request counts once.
        self._seen: set[str] = set()

    def _ingest(self, rows: Iterable[UsageRow]) -> int:
        n = 0
        for row in rows:
            self.watermark = max(self.watermark, row.row_id)
            dedup_key = row.request_id or row.message_id
            if dedup_key and dedup_key in self._seen:
                continue
            if dedup_key:
                self._seen.add(dedup_key)
            self.total.add(row)
            self.by_model.setdefault(row.model, UsageStats()).add(row)

            local = row.ts.astimezone()
            day = local.date().isoformat()
            self.by_day.setdefault(day, UsageStats()).add(row)
            self.by_day_model.setdefault(day, {}).setdefault(
                row.model, UsageStats()
            ).add(row)
            hour = local.strftime("%Y-%m-%dT%H")
            self.by_hour.setdefault(hour, UsageStats()).add(row)
            self.by_hour_model.setdefault(hour, {}).setdefault(
                row.model, UsageStats()
            ).add(row)

            wk = f"{local.weekday()}-{local.hour}"  # 0 = Monday
            self.by_weekhour.setdefault(wk, UsageStats()).add(row)
            self.by_weekhour_model.setdefault(wk, {}).setdefault(
                row.model, UsageStats()
            ).add(row)

            bucket = self.by_session.setdefault(row.session_id, SessionBucket())
            bucket.title = row.session_title
            bucket.working_directory = row.working_directory
            bucket.last_ts = max(bucket.last_ts, row.ts)
            bucket.by_model.setdefault(row.model, UsageStats()).add(row)

            self.recent.appendleft(
                {
                    "ts": row.ts.astimezone().isoformat(timespec="seconds"),
                    "model": row.model,
                    "session_title": row.session_title,
                    "session_id": row.session_id,
                    "input": row.input_tokens,
                    "output": row.output_tokens,
                    "cache_read": row.cache_read_tokens,
                    "cache_creation": row.cache_creation_tokens,
                    "ttft_ms": row.ttft_ms,
                    "total_ms": row.total_time_ms,
                    "tok_per_s": row.tokens_per_sec,
                    "request_id": row.request_id,
                    "message_id": row.message_id,
                }
            )
            n += 1
        return n

    def poll(self) -> int:
        """Fold new rows into the aggregates. Returns rows ingested."""
        with self.lock:
            conn = connect()
            try:
                self.new_requests = self._ingest(
                    fetch_usage_rows(conn, self.watermark)
                )
            finally:
                conn.close()
            return self.new_requests

    # ---- views -----------------------------------------------------------

    def day_stats(self, day: str | None = None) -> UsageStats:
        day = day or datetime.now().astimezone().date().isoformat()
        return self.by_day.get(day, UsageStats())

    def day_cost(self, day: str | None = None) -> float:
        day = day or datetime.now().astimezone().date().isoformat()
        return sum(
            self.stats_cost(s, m)
            for m, s in self.by_day_model.get(day, {}).items()
        )

    def hour_cost(self, hour: str) -> float:
        return sum(
            self.stats_cost(s, m)
            for m, s in self.by_hour_model.get(hour, {}).items()
        )

    def stats_cost(self, stats: UsageStats, model: str) -> float:
        p = self.prices.price_for(model)
        return p.cost(
            stats.input_tokens,
            stats.output_tokens,
            stats.cache_read_tokens,
            stats.cache_creation_tokens,
        )

    def model_rows(self) -> list[tuple[str, UsageStats, float]]:
        """(model, lifetime stats, cost) sorted by cost desc."""
        rows = [
            (m, s, self.stats_cost(s, m)) for m, s in self.by_model.items()
        ]
        rows.sort(key=lambda t: t[2], reverse=True)
        return rows

    def session_rows(self, limit: int = 10) -> list[tuple[str, SessionBucket, float]]:
        """Most recently active sessions: (session_id, bucket, cost)."""
        rows = [
            (sid, b, b.cost(self.prices)) for sid, b in self.by_session.items()
        ]
        rows.sort(key=lambda t: t[1].last_ts, reverse=True)
        return rows[:limit]

    def total_cost(self) -> float:
        return sum(cost for _, _, cost in self.model_rows())

    def _stats_dict(self, s: UsageStats, cost: float | None = None) -> dict:
        d = {
            "requests": s.requests,
            "input": s.input_tokens,
            "output": s.output_tokens,
            "cache_read": s.cache_read_tokens,
            "cache_creation": s.cache_creation_tokens,
            "total": s.total_tokens,
        }
        if cost is not None:
            d["cost"] = round(cost, 4)
        return d

    def request_body(self, request_id: str, message_id: str) -> str:
        """Lazily load one request's assistant reply text (on demand only —
        never carried in the snapshot)."""
        if not request_id and not message_id:
            return ""
        try:
            conn = connect()
            try:
                return fetch_message_body(conn, request_id, message_id)
            finally:
                conn.close()
        except Exception:
            return ""

    @staticmethod
    def _percentile(values: list[float], percentile: float) -> float | None:
        if not values:
            return None
        ordered = sorted(values)
        index = (len(ordered) - 1) * percentile
        lower = int(index)
        upper = min(lower + 1, len(ordered) - 1)
        value = ordered[lower] + (ordered[upper] - ordered[lower]) * (index - lower)
        return round(value, 2)

    def _period_stats(self, start: date, end: date) -> dict:
        days = [
            day for day in self.by_day
            if start <= date.fromisoformat(day) <= end
        ]
        stats = [self.by_day[day] for day in days]
        requests = sum(item.requests for item in stats)
        inputs = sum(item.input_tokens for item in stats)
        outputs = sum(item.output_tokens for item in stats)
        cache_read = sum(item.cache_read_tokens for item in stats)
        cache_creation = sum(item.cache_creation_tokens for item in stats)
        tokens = inputs + outputs + cache_read + cache_creation
        cost = sum(self.day_cost(day) for day in days)
        active_days = len(days)
        return {
            "start": start.isoformat(),
            "end": end.isoformat(),
            "calendar_days": (end - start).days + 1,
            "active_days": active_days,
            "requests": requests,
            "input": inputs,
            "output": outputs,
            "cache_read": cache_read,
            "cache_creation": cache_creation,
            "total": tokens,
            "cost": round(cost, 6),
            "avg_tokens_per_active_day": round(tokens / active_days) if active_days else 0,
            "avg_cost_per_active_day": round(cost / active_days, 6) if active_days else 0,
        }

    def _analytics(self, today: date) -> dict:
        last_7 = self._period_stats(today - timedelta(days=6), today)
        previous_7 = self._period_stats(today - timedelta(days=13), today - timedelta(days=7))
        last_30 = self._period_stats(today - timedelta(days=29), today)
        previous_30 = self._period_stats(today - timedelta(days=59), today - timedelta(days=30))
        month_to_date = self._period_stats(today.replace(day=1), today)
        month_days = calendar.monthrange(today.year, today.month)[1]
        projection_factor = month_days / today.day
        previous_cost = previous_7["cost"]
        previous_30_cost = previous_30["cost"]
        change = (
            round((last_7["cost"] - previous_cost) / previous_cost * 100, 1)
            if previous_cost else None
        )
        change_30 = (
            round((last_30["cost"] - previous_30_cost) / previous_30_cost * 100, 1)
            if previous_30_cost else None
        )
        model_efficiency = []
        cache_savings = 0.0
        for model, stats, cost in self.model_rows():
            price = self.prices.price_for(model)
            saved = max(price.input - price.cache_read, 0) * stats.cache_read_tokens / 1_000_000
            cache_savings += saved
            model_efficiency.append({
                "model": model,
                "requests": stats.requests,
                "total": stats.total_tokens,
                "tokens_per_request": round(stats.total_tokens / stats.requests) if stats.requests else 0,
                "output_input_ratio": round(stats.output_tokens / stats.input_tokens, 3) if stats.input_tokens else None,
                "cache_savings": round(saved, 6),
                "cost_per_1k_output": round(cost * 1000 / stats.output_tokens, 6) if stats.output_tokens else None,
                "cost": round(cost, 6),
            })
        recent = list(self.recent)
        token_samples = [
            r["input"] + r["output"] + r["cache_read"] + r["cache_creation"]
            for r in recent
        ]
        performance = {
            "sample_size": len(recent),
            "request_tokens": {
                "p50": self._percentile(token_samples, 0.50),
                "p90": self._percentile(token_samples, 0.90),
            },
        }
        for key in ("input", "output", "ttft_ms", "total_ms", "tok_per_s"):
            values = [float(r[key]) for r in recent if r.get(key) is not None]
            performance[key] = {
                "p50": self._percentile(values, 0.50),
                "p90": self._percentile(values, 0.90),
            }
        total = self.total
        total_cost = self.total_cost()
        return {
            "periods": {
                "last_7_days": last_7,
                "previous_7_days": previous_7,
                "last_30_days": last_30,
                "previous_30_days": previous_30,
                "month_to_date": month_to_date,
                "comparison_7d_pct": change,
                "comparison_30d_pct": change_30,
                "month_projection": {
                    "cost": round(month_to_date["cost"] * projection_factor, 2),
                    "tokens": round(month_to_date["total"] * projection_factor),
                    "calendar_days": month_days,
                    "elapsed_days": today.day,
                },
            },
            "economics": {
                "cache_savings_estimate": round(cache_savings, 6),
                "cache_read_tokens": total.cache_read_tokens,
                "output_input_ratio": round(total.output_tokens / total.input_tokens, 3) if total.input_tokens else None,
                "tokens_per_request": round(total.total_tokens / total.requests) if total.requests else 0,
                "cost_per_1k_output": round(total_cost * 1000 / total.output_tokens, 6) if total.output_tokens else None,
            },
            "performance": performance,
            "models": model_efficiency,
        }

    def snapshot(self) -> dict:
        """JSON-serializable view of all aggregates (thread-safe)."""
        with self.lock:
            today_date = datetime.now().astimezone().date()
            today_key = today_date.isoformat()
            models = []
            for m, s, c in self.model_rows():
                p = self.prices.price_for(m)
                models.append(
                    {
                        "model": m,
                        "price": {
                            "input": p.input,
                            "output": p.output,
                            "cache_read": p.cache_read,
                            "cache_creation": p.cache_creation,
                        },
                        "avg_speed": round(s.avg_speed, 1)
                        if s.avg_speed is not None
                        else None,
                        "avg_ttft_ms": round(s.avg_ttft_ms)
                        if s.avg_ttft_ms is not None
                        else None,
                        "hit_rate": round(s.hit_rate, 4)
                        if s.hit_rate is not None
                        else None,
                        **self._stats_dict(s, c),
                    }
                )
            days = []
            for day in sorted(self.by_day, reverse=True):
                s = self.by_day[day]
                days.append(
                    {"day": day, **self._stats_dict(s, self.day_cost(day))}
                )
            hours = []
            for hour in sorted(self.by_hour, reverse=True)[:48]:
                s = self.by_hour[hour]
                hours.append(
                    {"hour": hour, **self._stats_dict(s, self.hour_cost(hour))}
                )
            all_sessions = [
                (sid, b, b.cost(self.prices))
                for sid, b in self.by_session.items()
            ]

            def session_dict(sid, b, cost):
                return {
                    "id": sid,
                    "title": b.title,
                    "dir": b.working_directory,
                    "last_ts": b.last_ts.astimezone().isoformat(timespec="seconds"),
                    "models": sorted(b.by_model),
                    **self._stats_dict(b.stats, cost),
                }

            sessions = [
                session_dict(sid, b, cost)
                for sid, b, cost in sorted(
                    all_sessions, key=lambda t: t[1].last_ts, reverse=True
                )[:50]
            ]
            top_sessions = [
                session_dict(sid, b, cost)
                for sid, b, cost in sorted(
                    all_sessions, key=lambda t: t[2], reverse=True
                )[:10]
            ]
            heatmap = []
            for wk, s in self.by_weekhour.items():
                dow, hour = wk.split("-", 1)
                cost = sum(
                    self.stats_cost(ms, m)
                    for m, ms in self.by_weekhour_model.get(wk, {}).items()
                )
                heatmap.append(
                    {
                        "dow": int(dow),
                        "hour": int(hour),
                        "requests": s.requests,
                        "total": s.total_tokens,
                        "cost": round(cost, 4),
                    }
                )
            return {
                "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
                "meta": dict(self.meta),
                "poll": {"watermark": self.watermark, "new_requests": self.new_requests},
                "today": {
                    "day": today_key,
                    **self._stats_dict(
                        self.by_day.get(today_key, UsageStats()),
                        self.day_cost(today_key),
                    ),
                },
                "total": self._stats_dict(self.total, self.total_cost()),
                "by_day": days,
                "by_hour": hours,
                "by_model": models,
                "sessions": sessions,
                "top_sessions": top_sessions,
                "heatmap": heatmap,
                "analytics": self._analytics(today_date),
                "requests": self._recent_priced(),
                "settings": {
                    "daily_budget": self.prices.daily_budget,
                    "language": self.prices.language,
                    "theme": str(self.prices.settings.get("theme", "system") or "system"),
                },
            }

    def _recent_priced(self, limit: int | None = None) -> list[dict]:
        out = []
        rows = list(self.recent)
        if limit:
            rows = rows[:limit]
        for r in rows:
            p = self.prices.price_for(r["model"])
            out.append(
                {
                    **r,
                    "cost": round(
                        p.cost(
                            r["input"],
                            r["output"],
                            r["cache_read"],
                            r["cache_creation"],
                        ),
                        4,
                    ),
                }
            )
        return out


def format_tokens(n: int) -> str:
    if n >= 1_000_000_000:
        return f"{n / 1_000_000_000:.2f}B"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.2f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}k"
    return str(n)


def format_cost(c: float) -> str:
    if c >= 1:
        return f"${c:,.2f}"
    return f"${c:.4f}".rstrip("0").rstrip(".")
