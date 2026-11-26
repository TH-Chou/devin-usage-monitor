import csv
import io
import base64
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
import urllib.error
import urllib.request
import zipfile
from contextlib import closing
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch


EXTENSION_ROOT = Path(__file__).resolve().parents[1]
WORKER = EXTENSION_ROOT / "python" / "worker.py"
sys.path.insert(0, str(EXTENSION_ROOT / "python"))

import devin_token_monitor
from devin_token_monitor import pricing
from devin_token_monitor.aggregator import UsageAggregator, format_cost
from devin_token_monitor.db import UsageRow, connect, fetch_message_body

devin_token_monitor.__path__.append(str(EXTENSION_ROOT.parent / "devin_token_monitor"))
from devin_token_monitor.web import start_server


class WorkerProtocolTests(unittest.TestCase):
    def test_snapshot_body_and_csv_export(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            database = root / "sessions.db"
            prices = root / "prices.json"
            prices.write_text(json.dumps({
                "default": {},
                "models": {
                    "test-model": {
                        "input": 1.0,
                        "output": 2.0,
                        "cache_read": 0.5,
                        "cache_creation": 3.0,
                    }
                },
                "settings": {"language": "en"},
            }), encoding="utf-8")
            connection = sqlite3.connect(database)
            connection.executescript("""
                CREATE TABLE sessions (
                    id TEXT PRIMARY KEY,
                    title TEXT,
                    working_directory TEXT,
                    model TEXT
                );
                CREATE TABLE message_nodes (
                    row_id INTEGER PRIMARY KEY,
                    session_id TEXT,
                    chat_message TEXT,
                    created_at INTEGER
                );
            """)
            connection.execute(
                "INSERT INTO sessions VALUES (?, ?, ?, ?)",
                ("session-1", "Тестовая сессия — résumé", temp, "test-model"),
            )
            now = datetime.now(timezone.utc)
            message = {
                "message_id": "message-1",
                "content": "lazy response body",
                "metadata": {
                    "generation_model": "test-model",
                    "request_id": "request-1",
                    "created_at": now.isoformat().replace("+00:00", "Z"),
                    "metrics": {
                        "input_tokens": 1000000,
                        "output_tokens": 500000,
                        "cache_read_tokens": 200000,
                        "cache_creation_tokens": 100000,
                        "ttft_ms": 120,
                        "total_time_ms": 1000,
                        "tokens_per_sec": 500,
                    },
                },
            }
            connection.execute(
                "INSERT INTO message_nodes VALUES (?, ?, ?, ?)",
                (1, "session-1", json.dumps(message), int(now.timestamp())),
            )
            connection.commit()
            connection.close()

            env = os.environ.copy()
            env["DEVIN_SESSIONS_DB"] = str(database)
            env["DTM_PRICES"] = str(prices)
            env["PYTHONIOENCODING"] = "cp1251"
            requests = [
                {"id": 1, "action": "initialize"},
                {"id": 2, "action": "body", "request_id": "request-1", "message_id": "message-1"},
                {"id": 3, "action": "export"},
                {"id": 4, "action": "settings", "settings": {"theme": "ocean"}},
                {"id": 5, "action": "poll", "include_snapshot": False},
                {"id": 6, "action": "usageReport", "model": "test-model"},
            ]
            process = subprocess.run(
                [sys.executable, str(WORKER)],
                input="".join(json.dumps(item) + "\n" for item in requests),
                capture_output=True,
                encoding="utf-8",
                env=env,
                check=True,
            )
            responses = [json.loads(line) for line in process.stdout.splitlines()]
            self.assertEqual([item["id"] for item in responses], [1, 2, 3, 4, 5, 6])
            self.assertTrue(all(item["ok"] for item in responses), process.stderr)
            snapshot = responses[0]["result"]["snapshot"]
            self.assertEqual(snapshot["total"]["requests"], 1)
            self.assertEqual(snapshot["total"]["input"], 1000000)
            self.assertEqual(snapshot["sessions"][0]["title"], "Тестовая сессия — résumé")
            self.assertEqual(snapshot["settings"]["language"], "en")
            self.assertEqual(snapshot["settings"]["theme"], "system")
            analytics = snapshot["analytics"]
            self.assertEqual(analytics["periods"]["last_7_days"]["requests"], 1)
            self.assertEqual(analytics["periods"]["last_7_days"]["cost"], 2.4)
            self.assertEqual(analytics["economics"]["output_input_ratio"], 0.5)
            self.assertEqual(analytics["economics"]["cache_savings_estimate"], 0.1)
            self.assertEqual(analytics["performance"]["request_tokens"]["p90"], 1800000.0)
            self.assertEqual(analytics["models"][0]["cost_per_1k_output"], 0.0048)
            self.assertEqual(responses[1]["result"]["body"], "lazy response body")
            archive = zipfile.ZipFile(
                io.BytesIO(base64.b64decode(responses[2]["result"]["data"]))
            )
            self.assertEqual(set(archive.namelist()), {
                "requests.csv", "sessions.csv", "daily.csv", "models.csv"
            })
            self.assertIn("request-1", archive.read("requests.csv").decode("utf-8"))
            for kind in ("sessions", "models"):
                table = csv.DictReader(io.StringIO(archive.read(kind + ".csv").decode()))
                self.assertEqual(table.fieldnames[-1], "cache_creation")
                self.assertEqual(next(table)["cache_creation"], "100000")
            archive.close()
            self.assertEqual(responses[3]["result"]["snapshot"]["settings"]["theme"], "ocean")
            self.assertEqual(json.loads(prices.read_text(encoding="utf-8"))["settings"]["theme"], "ocean")
            summary = responses[4]["result"]["summary"]
            self.assertEqual(summary["today"]["requests"], 1)
            self.assertEqual(summary["settings"]["theme"], "ocean")
            self.assertNotIn("requests", summary)
            self.assertNotIn("snapshot", responses[4]["result"])
            report = responses[5]["result"]["report"]
            self.assertEqual(report["summary"]["cost"], 2.4)
            self.assertEqual(report["models"][0]["model"], "test-model")
            self.assertEqual(report["sessions"][0]["title"], "Тестовая сессия — résumé")
            self.assertNotIn("lazy response body", json.dumps(report))


class UsageReportTests(unittest.TestCase):
    def test_filters_and_rankings_include_evicted_rows_and_use_current_prices(self):
        prices = pricing.PriceTable(pricing.ModelPrice(input=1), {
            "b": pricing.ModelPrice(input=3, output=5, cache_read=1, cache_creation=4),
        })
        with patch("devin_token_monitor.aggregator.RECENT_LIMIT", 1):
            agg = UsageAggregator(prices)
        first = UsageRow(
            row_id=1, session_id="s1", session_title="First", working_directory="/one",
            model="a", request_id="r1", message_id="m1", input_tokens=1000000,
            output_tokens=0, cache_read_tokens=0, cache_creation_tokens=0, ttft_ms=None,
            total_time_ms=None, tokens_per_sec=None, ts=datetime(2026, 1, 1, 12).astimezone(),
        )
        second = replace(first, row_id=2, model="b", request_id="r2", session_id="s2",
                         session_title="Second", ts=datetime(2026, 1, 2, 12).astimezone(),
                         output_tokens=100000, cache_read_tokens=100000, cache_creation_tokens=50000)
        third = replace(first, row_id=3, request_id="r3", ts=second.ts)
        self.assertEqual(agg._ingest([first, second, third, replace(first, row_id=4)]), 3)
        self.assertEqual(len(agg.recent), 1)
        full = agg.usage_report()
        self.assertEqual(full["summary"]["requests"], 3)
        self.assertEqual(full["summary"]["cost"], 5.8)
        self.assertEqual(full["session_count"], 2)
        self.assertEqual([row["model"] for row in full["models"]], ["b", "a"])
        self.assertEqual([row["id"] for row in full["sessions"]], ["s2", "s1"])
        self.assertEqual([row["cost"] for row in full["daily"]], [1, 4.8])

        report = agg.usage_report("2026-01-02", "2026-01-02", "b")
        self.assertEqual(report["summary"], {
            "requests": 1, "total": 1250000, "input": 1000000, "output": 100000,
            "cache_read": 100000, "cache_creation": 50000, "cost": 3.8,
        })
        self.assertEqual(report["sessions"][0]["requests"], 1)
        self.assertEqual(agg.usage_report("2026-01-01", "2026-01-01", "b")["daily"], [])
        revision = agg.snapshot()["analytics"]["report_revision"]
        agg._ingest([])
        self.assertEqual(agg.snapshot()["analytics"]["report_revision"], revision)
        agg.prices = pricing.PriceTable(pricing.ModelPrice(), {})
        self.assertNotEqual(agg.snapshot()["analytics"]["report_revision"], revision)
        self.assertEqual(agg.usage_report()["summary"]["cost"], 0)

    def test_rejects_invalid_dates(self):
        agg = UsageAggregator(pricing.PriceTable(pricing.ModelPrice(), {}))
        for start, end in (("2026-02-30", ""), ("20260101", ""), ("2026-01-02", "2026-01-01")):
            with self.subTest(start=start, end=end), self.assertRaises(ValueError):
                agg.usage_report(start, end)


class CurrentModelPriceTests(unittest.TestCase):
    def test_latest_model_ids_use_official_standard_rates(self):
        table = pricing.PriceTable.load(EXTENSION_ROOT.parent / "prices.json")
        expected = {
            "gpt-6.2-astra": (8.0, 40.0),
            "gpt-6.2-sol": (2.0, 10.0),
            "claude-fable-5-2": (8.0, 40.0),
            "claude-opus-5-5": (4.0, 20.0),
            "claude-sonnet-5-5": (2.0, 10.0),
            "claude-haiku-5-5": (0.1, 0.5),
            "gemini-4-carbon": (2.0, 10.0),
            "gemini-4-argon": (2.0, 10.0),
            "gemini-4-hydrogen": (1.5, 7.5),
        }
        for model, rates in expected.items():
            with self.subTest(model=model):
                price = table.price_for(model)
                self.assertEqual((price.input, price.output), rates)


def make_usage_db(path, row_id, request_id, input_tokens):
    connection = sqlite3.connect(path)
    connection.executescript("""
        CREATE TABLE sessions (
            id TEXT PRIMARY KEY, title TEXT, working_directory TEXT, model TEXT
        );
        CREATE TABLE message_nodes (
            row_id INTEGER PRIMARY KEY, session_id TEXT, chat_message TEXT,
            created_at INTEGER
        );
    """)
    connection.execute(
        "INSERT INTO sessions VALUES (?, ?, ?, ?)",
        ("session-1", "Test", str(path.parent), "test-model"),
    )
    message = {
        "message_id": f"m-{row_id}",
        "content": f"body-{row_id}",
        "metadata": {
            "generation_model": "test-model",
            "request_id": request_id,
            "metrics": {"input_tokens": input_tokens},
        },
    }
    connection.execute(
        "INSERT INTO message_nodes VALUES (?, ?, ?, ?)",
        (row_id, "session-1", json.dumps(message), int(datetime.now(timezone.utc).timestamp())),
    )
    connection.commit()
    connection.close()


class DataReliabilityTests(unittest.TestCase):
    def test_single_token_cost_matches_across_reports_and_snapshot(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "sessions.db"
            make_usage_db(path, 1, "r1", 1)
            agg = UsageAggregator(pricing.PriceTable(pricing.ModelPrice(input=0.01), {}))
            with patch.dict(os.environ, {"DEVIN_SESSIONS_DB": str(path)}):
                agg.poll()
            for price, expected in ((0.01, 1e-8), (1e-8, 1e-14), (0, 0)):
                with self.subTest(price=price):
                    agg.prices = pricing.PriceTable(pricing.ModelPrice(input=price), {})
                    snapshot = agg.snapshot()
                    values = [snapshot[key][0]["cost"] for key in (
                        "by_model", "sessions", "by_day", "by_hour", "heatmap", "requests",
                    )]
                    values += [snapshot["total"]["cost"], snapshot["analytics"]["models"][0]["cost"],
                               agg.usage_report()["summary"]["cost"], agg.status_summary()["today"]["cost"]]
                    self.assertEqual(values, [expected] * len(values))
                    self.assertEqual(float(format_cost(expected).removeprefix("$")), expected)
                    self.assertEqual(agg.usage_report()["summary"]["total"], 1)

    def test_watermark_rewrite_and_manual_rebuild_in_wal(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "sessions.db"
            make_usage_db(path, 1, "r1", 1)
            agg = UsageAggregator(pricing.PriceTable(pricing.ModelPrice(input=1), {}))
            with closing(sqlite3.connect(path)) as writer, patch.dict(os.environ, {"DEVIN_SESSIONS_DB": str(path)}):
                writer.execute("PRAGMA journal_mode=WAL")
                agg.poll()
                original = agg.snapshot()["analytics"]["report_revision"]
                edit = """UPDATE message_nodes SET chat_message=json_set(
                    chat_message, '$.metadata.metrics.input_tokens', ?) WHERE row_id=1"""
                writer.execute(edit, (15,))
                writer.commit()
                agg.poll()
                self.assertEqual(agg.total.input_tokens, 15)
                self.assertNotEqual(agg.snapshot()["analytics"]["report_revision"], original)

                # A replacement tail can also coincide with a later append.
                writer.execute(edit, (5,))
                writer.execute("""INSERT INTO message_nodes
                    SELECT 2, session_id, json_set(chat_message, '$.metadata.request_id', 'r2',
                    '$.metadata.metrics.input_tokens', 8), created_at FROM message_nodes WHERE row_id=1""")
                writer.commit()
                agg.poll()
                self.assertEqual(agg.usage_report()["summary"]["input"], 13)
                self.assertEqual(agg.total.requests, 2)
                self.assertEqual(agg.poll(), 0)

                writer.execute(edit, (12,))
                writer.commit()
                agg.poll(rebuild=True)
                self.assertEqual(agg.usage_report()["summary"]["input"], 20)
                self.assertEqual(agg.meta["db_path"], str(path))

    def test_offsetless_timestamp_and_optional_metrics_do_not_interrupt_ingest(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "sessions.db"
            make_usage_db(path, 1, "r1", 8)
            instant = 1704103200
            with closing(sqlite3.connect(path)) as writer:
                writer.execute("""UPDATE message_nodes SET created_at=?, chat_message=json_set(
                    chat_message, '$.metadata.created_at', '2024-01-01T10:00:00',
                    '$.metadata.metrics.ttft_ms', '7.5', '$.metadata.metrics.tokens_per_sec', 'n/a')""",
                    (instant,))
                writer.commit()
            agg = UsageAggregator(pricing.PriceTable(pricing.ModelPrice(), {}))
            with patch.dict(os.environ, {"DEVIN_SESSIONS_DB": str(path)}):
                self.assertEqual(agg.poll(), 1)
                self.assertEqual(agg.poll(), 0)
            snapshot = agg.snapshot()
            request = snapshot["requests"][0]
            self.assertEqual(datetime.fromisoformat(request["ts"]).timestamp(), instant)
            self.assertEqual(request["ttft_ms"], 7.5)
            self.assertIsNone(request["tok_per_s"])
            self.assertEqual(agg.total.requests, 1)
            self.assertEqual(agg.total.input_tokens, 8)

    def test_missing_new_source_does_not_inherit_previous_source_totals(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "sessions.db"
            missing = Path(temp) / "other.db"
            make_usage_db(path, 1, "r1", 7)
            agg = UsageAggregator(pricing.PriceTable(pricing.ModelPrice(), {}))
            with patch.dict(os.environ, {"DEVIN_SESSIONS_DB": str(path)}):
                agg.poll()
            with patch.dict(os.environ, {"DEVIN_SESSIONS_DB": str(missing)}):
                with self.assertRaises(FileNotFoundError):
                    agg.poll()
            self.assertEqual(agg.meta["db_path"], str(missing))
            self.assertNotIn("poll_last_ok", agg.meta)
            self.assertEqual(agg.usage_report()["summary"]["requests"], 0)
            self.assertEqual(agg.snapshot()["requests"], [])

    def test_read_only_db_with_reserved_uri_characters(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "sessions #.db"
            make_usage_db(path, 1, "r1", 8)
            connection = connect(path)
            try:
                self.assertEqual(connection.execute("SELECT count(*) FROM message_nodes").fetchone()[0], 1)
                with self.assertRaises(sqlite3.OperationalError):
                    connection.execute("INSERT INTO sessions(id) VALUES ('new')")
            finally:
                connection.close()

    def test_missing_request_id_cannot_match_another_reply(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "sessions.db"
            connection = sqlite3.connect(path)
            connection.execute("CREATE TABLE message_nodes(row_id INTEGER PRIMARY KEY, chat_message TEXT)")
            connection.executemany(
                "INSERT INTO message_nodes VALUES (?, ?)",
                [
                    (1, json.dumps({"message_id": "other", "content": "wrong",
                                    "metadata": {"request_id": ""}})),
                    (2, json.dumps({"message_id": "target", "content": "correct",
                                    "metadata": {"request_id": "r-target"}})),
                ],
            )
            connection.commit()
            connection.close()
            readonly = connect(path)
            try:
                self.assertEqual(fetch_message_body(readonly, "", "target"), "correct")
                self.assertEqual(fetch_message_body(readonly, "", ""), "")
            finally:
                readonly.close()

    def test_database_replacement_and_truncation_rebuild_totals(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "sessions.db"
            make_usage_db(path, 10, "same-request", 10)
            aggregator = UsageAggregator(pricing.PriceTable(pricing.ModelPrice(), {}))
            with patch.dict(os.environ, {"DEVIN_SESSIONS_DB": str(path)}):
                aggregator.poll()
                self.assertEqual(aggregator.snapshot()["total"]["input"], 10)
                replacement = Path(temp) / "replacement.db"
                make_usage_db(replacement, 20, "same-request", 20)
                os.replace(replacement, path)
                aggregator.poll()
                self.assertEqual(aggregator.snapshot()["total"]["input"], 20)
                self.assertEqual(aggregator.snapshot()["total"]["requests"], 1)
                connection = sqlite3.connect(path)
                connection.execute("DELETE FROM message_nodes")
                message = {"message_id": "new-message", "metadata": {
                    "request_id": "new-request", "metrics": {"input_tokens": 7}}}
                connection.execute("INSERT INTO message_nodes VALUES (?, ?, ?, ?)",
                                   (1, "session-1", json.dumps(message),
                                    int(datetime.now(timezone.utc).timestamp())))
                connection.commit()
                connection.close()
                aggregator.poll()
                self.assertEqual(aggregator.snapshot()["total"]["input"], 7)
                self.assertEqual(aggregator.snapshot()["total"]["requests"], 1)
                self.assertEqual(aggregator.usage_report()["summary"]["input"], 7)

    def test_poll_failure_is_reported_and_cleared_on_recovery(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "sessions.db"
            aggregator = UsageAggregator(pricing.PriceTable(pricing.ModelPrice(), {}))
            with patch.dict(os.environ, {"DEVIN_SESSIONS_DB": str(path)}):
                with self.assertRaises(FileNotFoundError):
                    aggregator.poll()
                self.assertIn("poll_error", aggregator.status_summary()["meta"])
                make_usage_db(path, 1, "r1", 11)
                aggregator.poll()
                summary = aggregator.status_summary()
                self.assertNotIn("poll_error", summary["meta"])
                self.assertIn("poll_last_ok", summary["meta"])
                self.assertEqual(summary["today"]["input"], 11)

    def test_settings_use_user_copy_and_preserve_bundled_prices(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            bundled = root / "bundled.json"
            user = root / "user" / "prices.json"
            seed = {"default": {"input": 2}, "models": {"test-model": {"output": 3}},
                    "settings": {"language": "en"}}
            bundled.write_text(json.dumps(seed), encoding="utf-8")
            with patch.dict(os.environ, {"DTM_PRICES": ""}), \
                 patch.object(pricing, "_USER_FILE", user), \
                 patch.object(pricing, "_BUNDLED_FILE", bundled), \
                 patch.object(pricing, "_PROJECT_FILE", bundled):
                saved = pricing.PriceTable.load().update_settings({"language": "ru"})
                self.assertEqual(saved, user)
                self.assertEqual(pricing.PriceTable.load().language, "ru")
                saved = pricing.PriceTable.load().update_settings({"theme": "forest"})
                self.assertEqual(saved, user)
                self.assertEqual(json.loads(bundled.read_text(encoding="utf-8")), seed)
                raw = json.loads(user.read_text(encoding="utf-8"))
                self.assertEqual(raw["models"], seed["models"])
                self.assertEqual(raw["settings"], {"language": "ru", "theme": "forest"})
                with self.assertRaises(ValueError):
                    pricing.PriceTable.load().update_settings({"daily_budget": float("nan")})
                with self.assertRaises(ValueError):
                    pricing.PriceTable.load().update_settings({"theme": "unknown"})
                with self.assertRaises(ValueError):
                    pricing.ModelPrice.from_dict({"input": float("inf")})
                self.assertEqual(json.loads(user.read_text(encoding="utf-8")), raw)
                user.write_text("{invalid", encoding="utf-8")
                fallback = pricing.PriceTable.load()
                self.assertEqual(fallback.price_for("test-model").output, 3)
                with self.assertRaises(json.JSONDecodeError):
                    fallback.update_settings({"theme": "ocean"})
                self.assertEqual(user.read_text(encoding="utf-8"), "{invalid")

    def test_web_health_and_theme_settings_api(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            database = root / "sessions #.db"
            prices = root / "prices.json"
            make_usage_db(database, 1, "r1", 8)
            prices.write_text(json.dumps({"default": {}, "models": {}, "settings": {}}), encoding="utf-8")
            with patch.dict(os.environ, {
                "DEVIN_SESSIONS_DB": str(database),
                "DTM_PRICES": str(prices),
            }):
                aggregator = UsageAggregator(pricing.PriceTable.load())
                server, url = start_server(aggregator, host="127.0.0.1", port=0)
                try:
                    with self.assertRaises(urllib.error.HTTPError) as offline:
                        urllib.request.urlopen(url + "/api/health")
                    self.assertEqual(offline.exception.code, 503)
                    offline.exception.close()
                    aggregator.poll()
                    with urllib.request.urlopen(url + "/api/health") as response:
                        self.assertTrue(json.load(response)["ok"])
                    with urllib.request.urlopen(url + "/api/export.zip") as response:
                        self.assertEqual(response.headers.get_content_type(), "application/zip")
                        self.assertIn("attachment", response.headers["Content-Disposition"])
                        with zipfile.ZipFile(io.BytesIO(response.read())) as archive:
                            self.assertEqual(set(archive.namelist()), {
                                "requests.csv", "sessions.csv", "daily.csv", "models.csv",
                            })
                            with urllib.request.urlopen(url + "/api/export.csv?what=models") as single:
                                self.assertEqual(archive.read("models.csv"), single.read())
                    with urllib.request.urlopen(url + "/api/usage-report?model=test-model") as response:
                        self.assertEqual(json.load(response)["summary"]["input"], 8)
                    with self.assertRaises(urllib.error.HTTPError) as bad_report:
                        urllib.request.urlopen(url + "/api/usage-report?start=invalid")
                    self.assertEqual(bad_report.exception.code, 400)
                    bad_report.exception.close()
                    request = urllib.request.Request(
                        url + "/api/settings", data=b'{"theme":"forest"}',
                        headers={"Content-Type": "application/json"},
                    )
                    with urllib.request.urlopen(request) as response:
                        self.assertEqual(json.load(response)["settings"]["theme"], "forest")
                    invalid = urllib.request.Request(
                        url + "/api/settings", data=b'{"theme":"invalid"}',
                        headers={"Content-Type": "application/json"},
                    )
                    with self.assertRaises(urllib.error.HTTPError) as bad_setting:
                        urllib.request.urlopen(invalid)
                    self.assertEqual(bad_setting.exception.code, 400)
                    bad_setting.exception.close()
                finally:
                    server.shutdown()
                    server.server_close()


class DbPathResolutionTests(unittest.TestCase):
    def test_windows_candidates_prefer_appdata_and_keep_xdg_fallback(self):
        import devin_token_monitor.db as db
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            appdata_db = root / "Roaming" / "Devin" / "cli" / "sessions.db"
            xdg_db = root / "xdg" / "sessions.db"
            with patch.object(sys, "platform", "win32"), \
                 patch.object(db, "_XDG_DB_PATH", xdg_db), \
                 patch.dict(os.environ, {"APPDATA": str(root / "Roaming"),
                                         "DEVIN_SESSIONS_DB": ""}):
                self.assertEqual(db.db_path(), appdata_db)
                xdg_db.parent.mkdir(parents=True)
                xdg_db.touch()
                self.assertEqual(db.db_path(), xdg_db)
                appdata_db.parent.mkdir(parents=True)
                appdata_db.touch()
                self.assertEqual(db.db_path(), appdata_db)
                with patch.dict(os.environ, {"DEVIN_SESSIONS_DB": str(xdg_db)}):
                    self.assertEqual(db.db_path(), xdg_db)

    def test_windows_uses_roaming_appdata_when_environment_variable_is_empty(self):
        import devin_token_monitor.db as db
        with tempfile.TemporaryDirectory() as temp:
            with patch.object(sys, "platform", "win32"), \
                 patch.object(db, "_XDG_DB_PATH", Path(temp) / "missing" / "sessions.db"), \
                 patch.dict(os.environ, {"APPDATA": "", "DEVIN_SESSIONS_DB": ""}):
                expected = Path.home() / "AppData" / "Roaming" / "Devin" / "cli" / "sessions.db"
                self.assertEqual(db.db_path(), expected)


if __name__ == "__main__":
    unittest.main()
