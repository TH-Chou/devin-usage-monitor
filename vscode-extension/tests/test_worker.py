import base64
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
import zipfile
from datetime import datetime, timezone
from pathlib import Path


EXTENSION_ROOT = Path(__file__).resolve().parents[1]
WORKER = EXTENSION_ROOT / "python" / "worker.py"


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
            self.assertEqual([item["id"] for item in responses], [1, 2, 3, 4])
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


if __name__ == "__main__":
    unittest.main()
