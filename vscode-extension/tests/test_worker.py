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
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch


EXTENSION_ROOT = Path(__file__).resolve().parents[1]
WORKER = EXTENSION_ROOT / "python" / "worker.py"
sys.path.insert(0, str(EXTENSION_ROOT / "python"))

import devin_token_monitor
from devin_token_monitor import pricing
from devin_token_monitor.aggregator import UsageAggregator
from devin_token_monitor.db import connect, fetch_message_body

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
                ("session-1", "Worker Test", temp, "test-model"),
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
            requests = [
                {"id": 1, "action": "initialize"},
                {"id": 2, "action": "body", "request_id": "request-1", "message_id": "message-1"},
                {"id": 3, "action": "export"},
                {"id": 4, "action": "settings", "settings": {"theme": "ocean"}},
                {"id": 5, "action": "poll", "include_snapshot": False},
            ]
            process = subprocess.run(
                [sys.executable, str(WORKER)],
                input="".join(json.dumps(item) + "\n" for item in requests),
                capture_output=True,
                text=True,
                env=env,
                check=True,
            )
            responses = [json.loads(line) for line in process.stdout.splitlines()]
            self.assertEqual([item["id"] for item in responses], [1, 2, 3, 4, 5])
            self.assertTrue(all(item["ok"] for item in responses), process.stderr)
            snapshot = responses[0]["result"]["snapshot"]
            self.assertEqual(snapshot["total"]["requests"], 1)
            self.assertEqual(snapshot["total"]["input"], 1000000)
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
                __import__("io").BytesIO(base64.b64decode(responses[2]["result"]["data"]))
            )
            self.assertEqual(set(archive.namelist()), {
                "requests.csv", "sessions.csv", "daily.csv", "models.csv"
            })
            self.assertIn("request-1", archive.read("requests.csv").decode("utf-8"))
            self.assertEqual(responses[3]["result"]["snapshot"]["settings"]["theme"], "ocean")
            self.assertEqual(json.loads(prices.read_text(encoding="utf-8"))["settings"]["theme"], "ocean")
            summary = responses[4]["result"]["summary"]
            self.assertEqual(summary["today"]["requests"], 1)
            self.assertEqual(summary["settings"]["theme"], "ocean")
            self.assertNotIn("requests", summary)
            self.assertNotIn("snapshot", responses[4]["result"])


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
    def test_read_only_db_with_reserved_uri_characters(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "sessions #?.db"
            make_usage_db(path, 1, "r1", 8)
            with connect(path) as connection:
                self.assertEqual(connection.execute("SELECT count(*) FROM message_nodes").fetchone()[0], 1)
                with self.assertRaises(sqlite3.OperationalError):
                    connection.execute("INSERT INTO sessions(id) VALUES ('new')")

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
            with connect(path) as readonly:
                self.assertEqual(fetch_message_body(readonly, "", "target"), "correct")
                self.assertEqual(fetch_message_body(readonly, "", ""), "")

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
                saved = pricing.PriceTable.load().update_settings({"theme": "forest"})
                self.assertEqual(saved, user)
                self.assertEqual(json.loads(bundled.read_text(encoding="utf-8")), seed)
                raw = json.loads(user.read_text(encoding="utf-8"))
                self.assertEqual(raw["models"], seed["models"])
                self.assertEqual(raw["settings"], {"language": "en", "theme": "forest"})
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
            database = root / "sessions #?.db"
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


if __name__ == "__main__":
    unittest.main()
