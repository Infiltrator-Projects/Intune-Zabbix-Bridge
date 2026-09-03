import json
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from intune_zabbix_bridge import hardened
from intune_zabbix_bridge.collector import Config


class HardenedCollectorTests(unittest.TestCase):
    @staticmethod
    def config() -> Config:
        return Config(
            tenant_id="t",
            client_id="c",
            client_secret="s",
            telemetry_script_id="i",
            zabbix_server="127.0.0.1",
            zabbix_port=10051,
            zabbix_host="Microsoft Intune - Windows Fleet",
            zabbix_sender="zabbix_sender",
            timezone_name="Australia/Melbourne",
            max_telemetry_age_hours=48,
            top_n=10,
            http_timeout=20,
            http_retries=1,
        )

    def test_duplicate_hostname_with_distinct_ids_remains_two_devices(self):
        rows = hardened.parse_managed_windows_devices([
            {
                "id": "device-a",
                "deviceName": "SAME-PC",
                "userPrincipalName": "a@example.com",
                "operatingSystem": "Windows",
                "lastSyncDateTime": "2026-09-04T00:00:00Z",
            },
            {
                "id": "device-b",
                "deviceName": "SAME-PC",
                "userPrincipalName": "b@example.com",
                "operatingSystem": "Windows",
                "lastSyncDateTime": "2026-09-04T00:01:00Z",
            },
        ])
        self.assertEqual(len(rows), 2)
        self.assertEqual({row.managed_device_id for row in rows}, {"device-a", "device-b"})

    def test_telemetry_is_keyed_by_managed_device_id_not_hostname(self):
        now = datetime(2026, 9, 4, 2, 0, tzinfo=timezone.utc)
        telemetry = hardened.parse_run_states([
            {
                "preRemediationDetectionScriptOutput":
                    "DEVICE=SAME-PC;LASTBOOT=2026-09-03T00:00:00Z;UPTIME_HOURS=26",
                "lastStateUpdateDateTime": "2026-09-04T01:30:00Z",
                "managedDevice": {
                    "id": "device-b",
                    "deviceName": "SAME-PC",
                    "userPrincipalName": "b@example.com",
                },
            }
        ], now=now, max_age_hours=48)
        fleet = hardened.merge_fleet_devices(
            [
                hardened.ManagedDevice("device-a", "SAME-PC", "a@example.com"),
                hardened.ManagedDevice("device-b", "SAME-PC", "b@example.com"),
            ],
            [],
            telemetry,
        )
        by_id = {row.managed_device_id: row for row in fleet}
        self.assertEqual(by_id["device-a"].telemetry_status, "missing")
        self.assertEqual(by_id["device-b"].telemetry_status, "fresh")

    def test_ambiguous_ring_report_is_not_attached_by_hostname(self):
        managed = [
            hardened.ManagedDevice("device-a", "SAME-PC", "shared@example.com"),
            hardened.ManagedDevice("device-b", "SAME-PC", "shared@example.com"),
        ]
        reports = hardened.attach_ring_reports(managed, [{
            "deviceDisplayName": "SAME-PC",
            "userPrincipalName": "shared@example.com",
            "status": "compliant",
            "lastReportedDateTime": "2026-09-04T01:00:00Z",
            "_ring_id": "ring-a",
            "_ring_name": "Ring A",
        }])
        self.assertEqual(reports, [])

    def test_unique_ring_report_can_be_attached_safely(self):
        managed = [
            hardened.ManagedDevice("device-a", "PC-A", "a@example.com"),
            hardened.ManagedDevice("device-b", "PC-B", "b@example.com"),
        ]
        reports = hardened.attach_ring_reports(managed, [{
            "deviceDisplayName": "PC-B",
            "userPrincipalName": "b@example.com",
            "status": "compliant",
            "lastReportedDateTime": "2026-09-04T01:00:00Z",
            "_ring_id": "ring-a",
            "_ring_name": "Ring A",
        }])
        self.assertEqual(len(reports), 1)
        self.assertEqual(reports[0].managed_device_id, "device-b")

    def test_metrics_do_not_collapse_duplicate_hostnames(self):
        now = datetime(2026, 9, 4, 2, 0, tzinfo=timezone.utc)
        records = [
            hardened.FleetDevice(
                "device-a", "SAME-PC", "a@example.com", (), 0, "none",
                "not-reported", None, None, None, None, None, "missing"
            ),
            hardened.FleetDevice(
                "device-b", "SAME-PC", "b@example.com", (), 0, "none",
                "not-reported", None, None, None, None, None, "missing"
            ),
        ]
        metrics = hardened.build_metrics(records, config=self.config(), now=now)
        summary = json.loads(metrics[hardened.SUMMARY_KEY])
        self.assertEqual(summary["expected_devices"], 2)
        self.assertEqual(
            {item["managed_device_id"] for item in summary["devices"]},
            {"device-a", "device-b"},
        )

    def test_summary_is_generation_commit_marker_and_is_sent_last(self):
        sent = []

        def sender(_config, key, value):
            sent.append((key, value))

        hardened.send_metrics(
            self.config(),
            {"metric.a": "1", "metric.b": "2", hardened.SUMMARY_KEY: "{}"},
            sender=sender,
        )
        self.assertEqual(sent[-1][0], hardened.SUMMARY_KEY)

    def test_summary_does_not_advance_after_companion_metric_failure(self):
        sent = []

        def sender(_config, key, value):
            sent.append((key, value))
            if key == "metric.b":
                raise RuntimeError("simulated sender failure")

        with self.assertRaises(RuntimeError):
            hardened.send_metrics(
                self.config(),
                {"metric.a": "1", "metric.b": "2", hardened.SUMMARY_KEY: "{}"},
                sender=sender,
            )
        self.assertNotIn(hardened.SUMMARY_KEY, [key for key, _ in sent])

    def test_zero_managed_windows_devices_fails_closed(self):
        with patch.object(hardened.legacy, "get_access_token", return_value="token"), \
             patch.object(hardened, "fetch_managed_windows_devices", return_value=[]):
            with self.assertRaisesRegex(RuntimeError, "zero managed Windows devices"):
                hardened.collect(self.config())


if __name__ == "__main__":
    unittest.main()
