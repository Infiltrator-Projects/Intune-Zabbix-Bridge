import json
import unittest
from dataclasses import replace
from datetime import datetime, timezone

from intune_zabbix_bridge.collector import (
    Config,
    ManagedWindowsDevice,
    build_metrics,
    merge_fleet_devices,
    parse_datetime,
    parse_managed_windows_devices,
    parse_run_states,
)


class CollectorTests(unittest.TestCase):
    def test_parse_datetime_z(self):
        value = parse_datetime("2026-09-02T01:26:55Z")
        self.assertEqual(value.tzinfo, timezone.utc)
        self.assertEqual(value.hour, 1)

    def test_parse_and_deduplicate(self):
        now = datetime(2026, 9, 2, 2, 0, tzinfo=timezone.utc)
        states = [
            {
                "preRemediationDetectionScriptOutput": "DEVICE=PC1;LASTBOOT=2026-09-01T00:00:00Z;UPTIME_HOURS=26",
                "lastStateUpdateDateTime": "2026-09-02T01:00:00Z",
                "managedDevice": {"deviceName": "PC1", "userPrincipalName": "u@example.com"},
            },
            {
                "preRemediationDetectionScriptOutput": "DEVICE=PC1;LASTBOOT=2026-09-01T02:00:00Z;UPTIME_HOURS=24",
                "lastStateUpdateDateTime": "2026-09-02T01:30:00Z",
                "managedDevice": {"deviceName": "PC1", "userPrincipalName": "u@example.com"},
            },
        ]
        records = parse_run_states(states, now=now, max_age_hours=48)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].last_restart.hour, 2)

    def test_managed_inventory_deduplicates_and_keeps_newest(self):
        devices = [
            {"deviceName": "PC1", "userPrincipalName": "old@example.com", "operatingSystem": "Windows", "lastSyncDateTime": "2026-09-01T00:00:00Z"},
            {"deviceName": "pc1", "userPrincipalName": "new@example.com", "operatingSystem": "Windows", "lastSyncDateTime": "2026-09-02T00:00:00Z"},
            {"deviceName": "PHONE", "userPrincipalName": "phone@example.com", "operatingSystem": "Android", "lastSyncDateTime": "2026-09-02T00:00:00Z"},
        ]
        records = parse_managed_windows_devices(devices)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].user, "new@example.com")

    def test_missing_telemetry_device_remains_visible(self):
        now = datetime(2026, 9, 2, 2, 0, tzinfo=timezone.utc)
        telemetry = parse_run_states([{
            "preRemediationDetectionScriptOutput": "DEVICE=PC1;LASTBOOT=2026-09-01T00:00:00Z;UPTIME_HOURS=26",
            "lastStateUpdateDateTime": "2026-09-02T01:30:00Z",
            "managedDevice": {"deviceName": "PC1", "userPrincipalName": "one@example.com"},
        }], now=now, max_age_hours=48)
        fleet = merge_fleet_devices([
            ManagedWindowsDevice("PC1", "one@example.com"),
            ManagedWindowsDevice("PC2", "two@example.com"),
        ], telemetry)
        by_name = {r.computer_name: r for r in fleet}
        self.assertEqual(by_name["PC1"].telemetry_status, "fresh")
        self.assertEqual(by_name["PC2"].telemetry_status, "missing")
        self.assertIsNone(by_name["PC2"].uptime_days)

    def test_metrics_sort_longest_first(self):
        now = datetime(2026, 9, 2, 2, 0, tzinfo=timezone.utc)
        states = [
            {
                "preRemediationDetectionScriptOutput": "DEVICE=NEWER;LASTBOOT=2026-09-01T00:00:00Z;UPTIME_HOURS=26",
                "lastStateUpdateDateTime": "2026-09-02T01:30:00Z",
                "managedDevice": {"deviceName": "NEWER", "userPrincipalName": "n@example.com"},
            },
            {
                "preRemediationDetectionScriptOutput": "DEVICE=OLDER;LASTBOOT=2026-08-20T00:00:00Z;UPTIME_HOURS=312",
                "lastStateUpdateDateTime": "2026-09-02T01:30:00Z",
                "managedDevice": {"deviceName": "OLDER", "userPrincipalName": "o@example.com"},
            },
        ]
        telemetry = parse_run_states(states, now=now, max_age_hours=48)
        records = merge_fleet_devices([
            ManagedWindowsDevice("NEWER", "n@example.com"),
            ManagedWindowsDevice("OLDER", "o@example.com"),
            ManagedWindowsDevice("MISSING", "m@example.com"),
        ], telemetry)
        config = Config(
            tenant_id="t", client_id="c", client_secret="s", telemetry_script_id="i",
            zabbix_server="127.0.0.1", zabbix_port=10051,
            zabbix_host="Microsoft Intune - Windows Fleet", zabbix_sender="zabbix_sender",
            timezone_name="Australia/Melbourne", max_telemetry_age_hours=48,
            top_n=10, http_timeout=20, http_retries=1,
        )
        metrics = build_metrics(records, config=config, now=now)
        lines = metrics["intune.windows.top10"].splitlines()
        self.assertIn("OLDER", lines[2])
        self.assertIn("NEWER", lines[3])

        limited_metrics = build_metrics(
            records, config=replace(config, top_n=1), now=now
        )
        summary = json.loads(limited_metrics["intune.windows.summary.json"])
        self.assertEqual(summary["expected_devices"], 3)
        self.assertEqual(summary["reporting_devices"], 2)
        self.assertEqual(summary["missing_devices"], 1)
        self.assertEqual(len(summary["devices"]), 3)
        self.assertEqual(len(summary["top"]), 1)
        self.assertEqual(summary["devices"][0]["computer_name"], "OLDER")
        self.assertEqual(summary["devices"][-1]["computer_name"], "MISSING")
        self.assertIsNone(summary["devices"][-1]["uptime_days"])


if __name__ == "__main__":
    unittest.main()
