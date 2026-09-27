"""macOS menu bar app that live-monitors Devin CLI token usage.

Run with:  .venv/bin/python -m devin_token_monitor.app
"""

from __future__ import annotations

import subprocess
import sys

import rumps

from .aggregator import UsageAggregator, format_cost, format_tokens
from .db import db_path
from .pricing import PriceTable, default_prices_path
from .web import start_server

POLL_SECONDS = 15


def _stats_text(s) -> str:
    return (
        f"in {format_tokens(s.input_tokens)} · out {format_tokens(s.output_tokens)} "
        f"· cached {format_tokens(s.cache_read_tokens)} · {s.requests} req"
    )


class DevinTokenMonitor(rumps.App):
    def __init__(self):
        super().__init__("⚡…", quit_button=None)
        self.agg = UsageAggregator(PriceTable.load())
        self.dashboard_url = None
        try:
            _srv, self.dashboard_url = start_server(self.agg)
        except OSError as e:
            print(f"dashboard disabled: {e}", file=sys.stderr)

        self.item_today = rumps.MenuItem("Today: —")
        self.item_total = rumps.MenuItem("All time: —")
        self.menu_models = rumps.MenuItem("By model")
        self.menu_sessions = rumps.MenuItem("Recent sessions")
        self.menu_days = rumps.MenuItem("By day")

        items = [
            self.item_today,
            self.item_total,
            None,
            self.menu_models,
            self.menu_sessions,
            self.menu_days,
            None,
        ]
        if self.dashboard_url:
            items.append(
                rumps.MenuItem(
                    f"Open dashboard ({self.dashboard_url})",
                    callback=self.on_open_dashboard,
                )
            )
        items += [
            rumps.MenuItem("Refresh now", callback=self.on_refresh),
            rumps.MenuItem("Edit prices.json…", callback=self.on_edit_prices),
            rumps.MenuItem("Quit", callback=rumps.quit_application),
        ]
        self.menu = items

        try:
            self.agg.poll()
        except FileNotFoundError:
            self.item_today.title = "Devin sessions.db not found"
        self._rebuild_menu()
        self._timer = rumps.Timer(self.on_poll, POLL_SECONDS)
        self._timer.start()

    # ---- updates ---------------------------------------------------------

    def on_poll(self, _timer):
        try:
            self.agg.poll()
        except Exception as e:  # keep the app alive; surface in menu
            self.item_today.title = f"poll error: {e}"
            return
        self._rebuild_menu()

    def on_refresh(self, _item):
        self.agg.prices = PriceTable.load()  # pick up price edits too
        self.on_poll(None)

    def on_edit_prices(self, _item):
        subprocess.Popen(["open", "-t", str(default_prices_path())])

    def on_open_dashboard(self, _item):
        subprocess.Popen(["open", self.dashboard_url])

    def _rebuild_menu(self):
        agg = self.agg
        today = agg.day_stats()
        today_cost = agg.day_cost()
        self.title = f"⚡{format_cost(today_cost)}"

        self.item_today.title = (
            f"Today: {format_cost(today_cost)} — {_stats_text(today)}"
        )
        self.item_total.title = (
            f"All time: {format_cost(agg.total_cost())} — {_stats_text(agg.total)}"
        )

        if len(self.menu_models):
            self.menu_models.clear()
        for model, s, cost in agg.model_rows():
            self.menu_models.add(
                rumps.MenuItem(f"{model} — {format_cost(cost)} ({_stats_text(s)})")
            )
        if not self.menu_models:
            self.menu_models.add(rumps.MenuItem("(no data)"))

        if len(self.menu_sessions):
            self.menu_sessions.clear()
        for _sid, b, cost in agg.session_rows(10):
            s = b.stats
            when = b.last_ts.astimezone().strftime("%m-%d %H:%M")
            title = b.title if len(b.title) <= 40 else b.title[:37] + "…"
            self.menu_sessions.add(
                rumps.MenuItem(f"{when} · {format_cost(cost)} · {title}")
            )
        if not self.menu_sessions:
            self.menu_sessions.add(rumps.MenuItem("(no data)"))

        if len(self.menu_days):
            self.menu_days.clear()
        for day in sorted(agg.by_day, reverse=True)[:7]:
            s = agg.by_day[day]
            self.menu_days.add(
                rumps.MenuItem(
                    f"{day} — {format_cost(agg.day_cost(day))} ({_stats_text(s)})"
                )
            )
        if not self.menu_days:
            self.menu_days.add(rumps.MenuItem("(no data)"))


def main() -> int:
    try:
        DevinTokenMonitor().run()
    except FileNotFoundError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
