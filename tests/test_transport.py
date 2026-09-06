import base64
import contextlib
import io
import json
import os
from pathlib import Path
import random
import shutil
import string
import subprocess
import unittest
import zlib
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from intune_zabbix_bridge import current, hardened, transport
import test_current


class SummaryTransportTests(unittest.TestCase):
    def fleet(self, count):
        now = datetime(2026, 9, 7, 0, 0, tzinfo=timezone.utc)
        states = []
        for index in range(count):
            state = test_current.CurrentRuntimeTests.state(
                f"device-{index}", f"S25-{index:011d}",
                (now - timedelta(minutes=index * 7)).isoformat(),
            )
            state["managedDevice"]["userPrincipalName"] = (
                f"élève-{index:04d}@sakyabram.vic.edu.au"
            )
            last_boot = (now - timedelta(hours=index * 13 + 1)).isoformat()
            state["preRemediationDetectionScriptOutput"] = (
                f"DEVICE=S25-{index:011d};LASTBOOT={last_boot};UPTIME_HOURS=1"
            )
            states.append(state)
        with patch.object(current.legacy, "get_access_token", return_value="token"), \
             patch.object(current.legacy, "fetch_run_states", return_value=states), \
             patch.object(current.legacy, "evaluate_reboot_requirement",
                          current.evaluate_reboot_telemetry_only), \
             patch.object(current, "datetime") as mocked_datetime:
            mocked_datetime.now.return_value = now
            return current.collect_telemetry_only(test_current.CurrentRuntimeTests.config())

    def test_large_fleets_publish_all_rows_and_summary_last(self):
        for count in (250, 1000):
            with self.subTest(devices=count):
                _, metrics = self.fleet(count)
                raw = metrics[hardened.SUMMARY_KEY]
                self.assertGreater(len(raw.encode("utf-8")), 76_550)
                sent = []
                hardened.send_metrics(
                    test_current.CurrentRuntimeTests.config(), metrics,
                    sender=lambda _config, key, value: sent.append((key, value)),
                )
                key, wire = sent[-1]
                self.assertEqual(key, hardened.SUMMARY_KEY)
                self.assertEqual(len(sent), len(metrics))
                self.assertLessEqual(len(wire.encode("utf-8")), 64_000)
                envelope = json.loads(wire)
                self.assertEqual(envelope["transport"], transport.TRANSPORT)
                decoded = zlib.decompress(base64.b64decode(envelope["data"]))
                self.assertEqual(envelope["uncompressed_bytes"], len(decoded))
                self.assertEqual(decoded, raw.encode("utf-8"))
                self.assertEqual(len(json.loads(decoded)["devices"]), count)
                self.assertEqual(metrics[hardened.SUMMARY_KEY], raw)
                self.assertEqual(dict(sent[:-1]), {
                    k: v for k, v in metrics.items() if k != hardened.SUMMARY_KEY
                })

    def test_exact_wire_boundary_and_small_history_remain_plain_json(self):
        prefix = '{"generated_at":"2026-09-07T00:00:00Z","devices":[],"padding":"'
        raw = prefix + "x" * (64_000 - len(prefix) - 2) + '"}'
        self.assertEqual(len(raw), 64_000)
        self.assertEqual(transport.encode_summary(raw), raw)
        larger = raw[:-2] + 'x"}'
        self.assertEqual(len(larger), 64_001)
        self.assertEqual(json.loads(transport.encode_summary(larger))["transport"],
                         transport.TRANSPORT)

    def test_uncompressible_summary_does_not_publish_any_metrics(self):
        rng = random.Random(7312)
        raw = json.dumps({"generated_at": "2026-09-07T00:00:00Z", "devices": [{
            "computer_name": "LONG-RECORD",
            "user": "".join(rng.choices(string.ascii_letters + string.digits, k=100_000)),
        }]})
        sent = []
        with self.assertRaisesRegex(RuntimeError, "even after compression"):
            hardened.send_metrics(
                test_current.CurrentRuntimeTests.config(),
                {"metric.a": "1", hardened.SUMMARY_KEY: raw},
                sender=lambda *args: sent.append(args),
            )
        self.assertEqual(sent, [])

    def test_decoded_budget_is_checked_before_compression(self):
        with self.assertRaisesRegex(RuntimeError, "decoded size limit"):
            transport.encode_summary("x" * (transport.MAX_DECODED_BYTES + 1))

    def test_missing_summary_does_not_publish_companions(self):
        sent = []
        with self.assertRaisesRegex(RuntimeError, "summary metric is missing"):
            hardened.send_metrics(
                test_current.CurrentRuntimeTests.config(), {"metric.a": "1"},
                sender=lambda *args: sent.append(args),
            )
        self.assertEqual(sent, [])

    def test_large_summary_logging_and_dry_run_use_readable_json(self):
        records, metrics = self.fleet(250)
        with patch.object(hardened, "collect", return_value=(records, metrics)), \
             patch.object(hardened.legacy.Config, "from_env",
                          return_value=test_current.CurrentRuntimeTests.config()), \
             patch.object(hardened, "_send_metric") as sender:
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(hardened.main(["--dry-run", "--json"]), 0)
            self.assertEqual(json.loads(output.getvalue()),
                             json.loads(metrics[hardened.SUMMARY_KEY]))
            sender.assert_not_called()
            self.assertEqual(hardened.main([]), 0)
            wire = sender.call_args.args[2]
            self.assertEqual(json.loads(wire)["transport"], transport.TRANSPORT)

    @unittest.skipUnless(shutil.which("php"), "PHP CLI required for widget round-trip")
    def test_python_transport_round_trips_through_actual_php_widget(self):
        root = Path(__file__).resolve().parents[1]
        widget = Path(os.environ.get(
            "INTUNE_TEST_WIDGET_ROOT", root / "module" / "intune_reboot_watch"
        ))
        code = (
            'require $argv[1]; '
            '$p = new \\Modules\\IntuneRebootWatch\\Includes\\FleetSummary(); '
            'echo json_encode($p->parse(stream_get_contents(STDIN), 10), '
            'JSON_THROW_ON_ERROR);'
        )
        for count in (176, 250, 1000):
            with self.subTest(devices=count):
                _, metrics = self.fleet(count)
                raw = metrics[hardened.SUMMARY_KEY]
                results = []
                for value in (raw, transport.encode_summary(raw)):
                    result = subprocess.run(
                        ["php", "-r", code, str(widget / "includes" / "FleetSummary.php")],
                        input=value, capture_output=True, text=True, check=True,
                    )
                    results.append(json.loads(result.stdout))
                self.assertEqual(results[0], results[1])
                self.assertEqual(len(results[1]["devices"]), count)
                self.assertEqual(results[1]["expected_devices"], count)
                self.assertEqual(len(results[1]["top"]), 10)


if __name__ == "__main__":
    unittest.main()
