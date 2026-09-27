"""Print a one-shot token usage report.

Usage:  python -m devin_token_monitor.cli
"""

from __future__ import annotations

import sys
from datetime import datetime

from .aggregator import UsageAggregator, format_cost, format_tokens
from .db import db_path
from .pricing import PriceTable


def _stats_line(s) -> str:
    return (
        f"in {format_tokens(s.input_tokens):>7}  out {format_tokens(s.output_tokens):>7}  "
        f"cached {format_tokens(s.cache_read_tokens):>7}  ({s.requests} req)"
    )


def main() -> int:
    try:
        agg = UsageAggregator(PriceTable.load())
        agg.poll()
    except FileNotFoundError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    today = agg.day_stats()
    print(f"Devin token usage — {db_path()}")
    print(f"generated {datetime.now().astimezone():%Y-%m-%d %H:%M:%S}\n")

    print(f"Today     {_stats_line(today)}  ~{format_cost(agg.day_cost())}")
    print(f"All time  {_stats_line(agg.total)}  ~{format_cost(agg.total_cost())}")

    print("\nBy model (all time):")
    for model, s, cost in agg.model_rows():
        print(f"  {model:<20} {_stats_line(s)}  ~{format_cost(cost)}")

    print("\nRecent sessions:")
    for sid, b, cost in agg.session_rows(10):
        s = b.stats
        when = b.last_ts.astimezone().strftime("%m-%d %H:%M")
        print(f"  {when}  ~{format_cost(cost):>8}  {format_tokens(s.total_tokens):>7} tok  {b.title}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
