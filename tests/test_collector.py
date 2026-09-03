import json
import unittest
from dataclasses import replace
from datetime import datetime, timezone

from intune_zabbix_bridge.collector import (
    Config,
    ManagedWindowsDevice,
    RingReport,
    build_metrics,
    merge_fleet_devices,
    parse_datetime,
    parse_managed_windows_devices,
    parse_ring_reports,
    parse_run_states,
)


class CollectorTests(unittest.TestCase):
    def test_parse_datetime_z(self):
        value = parse_datetime("2026-09-02T01:26:55Z")
        self.assertEqual(value.tzinfo, timezone.utc)
        self.assertEqual(value.hour, 1)

    def test_parse_and_deduplicate_telemetry(self):
        now = datetime(2026, 9, 2, 2, 0, tzinfo=timezone.utc)
        states = [
            {
                "preRemediationDetectionScriptOutput":
                    "DEVICE=PC1;LASTBOOT=2026-09-01T00:00:00Z;UPTIME_HOURS=26",
                "lastStateUpdateDateTime": "2026-09-02T01:00:00Z",
                "managedDevice": {
                    "deviceName": "PC1",
                    "userPrincipalName": "u@example.com",
                },
            },
            {
                "preRemediationDetectionScriptOutput":
                    "DEVICE=PC1;LASTBOOT=2026-09-01T02:00:00Z;UPTIME_HOURS=24",
                "lastStateUpdateDateTime": "2026-09-02T01:30:00Z",
                "managedDevice": {
                    "deviceName": "PC1",
                    "userPrincipalName": "u@example.com",
                },
            },
        ]
        records = parse_run_states(
            states,
            now=now,
            max_age_hours=48,
        )
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].last_restart.hour, 2)

    def test_managed_inventory_deduplicates_and_keeps_newest(self):
        devices = [
            {
                "deviceName": "PC1",
                "userPrincipalName": "old@example.com",
                "operatingSystem": "Windows",
                "lastSyncDateTime": "2026-09-01T00:00:00Z",
            },
            {
                "deviceName": "pc1",
                "userPrincipalName": "new@example.com",
                "operatingSystem": "Windows",
                "lastSyncDateTime": "2026-09-02T00:00:00Z",
            },
            {
                "deviceName": "PHONE",
                "userPrincipalName": "phone@example.com",
                "operatingSystem": "Android",
                "lastSyncDateTime": "2026-09-02T00:00:00Z",
            },
        ]
        records = parse_managed_windows_devices(devices)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].user, "new@example.com")

    def test_ring_reports_deduplicate_per_device_and_ring(self):
        reports = parse_ring_reports([
            {
                "deviceDisplayName": "PC1",
                "userPrincipalName": "u@example.com",
                "status": "pending",
                "lastReportedDateTime": "2026-09-02T01:00:00Z",
                "_ring_id": "ring-a",
                "_ring_name": "Ring A",
            },
            {
                "deviceDisplayName": "PC1",
                "userPrincipalName": "u@example.com",
                "status": "compliant",
                "lastReportedDateTime": "2026-09-02T01:30:00Z",
                "_ring_id": "ring-a",
                "_ring_name": "Ring A",
            },
        ])
        self.assertEqual(len(reports), 1)
        self.assertEqual(reports[0].status, "compliant")
        self.assertEqual(reports[0].ring_name, "Ring A")

    def test_ring_reported_device_without_telemetry_stays_visible(self):
        fleet = merge_fleet_devices(
            [
                ManagedWindowsDevice(
                    "S25-TEST",
                    "3954@example.com",
                )
            ],
            [
                RingReport(
                    computer_name="S25-TEST",
                    user="3954@example.com",
                    ring_id="even",
                    ring_name="Update policy Students ending in Even numbers",
                    status="compliant",
                    last_reported=datetime(
                        2026,
                        9,
                        3,
                        4,
                        17,
                        tzinfo=timezone.utc,
                    ),
                )
            ],
            [],
        )
        self.assertEqual(len(fleet), 1)
        record = fleet[0]
        self.assertEqual(record.ring_state, "one")
        self.assertEqual(record.ring_status, "compliant")
        self.assertEqual(record.ring_count, 1)
        self.assertEqual(record.telemetry_status, "missing")
        self.assertIsNone(record.uptime_days)

    def test_windows_device_with_no_ring_report_stays_visible_as_fault(self):
        fleet = merge_fleet_devices(
            [ManagedWindowsDevice("PC-NO-RING", "u@example.com")],
            [],
            [],
        )
        self.assertEqual(len(fleet), 1)
        self.assertEqual(fleet[0].ring_state, "none")
        self.assertEqual(fleet[0].ring_status, "not-reported")
        self.assertEqual(fleet[0].telemetry_status, "missing")

    def test_multiple_ring_reports_are_explicit(self):
        reports = [
            RingReport(
                "PC-MULTI",
                "u@example.com",
                "ring-a",
                "Ring A",
                "compliant",
                datetime(2026, 9, 2, 1, 0, tzinfo=timezone.utc),
            ),
            RingReport(
                "PC-MULTI",
                "u@example.com",
                "ring-b",
                "Ring B",
                "compliant",
                datetime(2026, 9, 2, 1, 5, tzinfo=timezone.utc),
            ),
        ]
        fleet = merge_fleet_devices(
            [ManagedWindowsDevice("PC-MULTI", "u@example.com")],
            reports,
            [],
        )
        self.assertEqual(fleet[0].ring_state, "multiple")
        self.assertEqual(fleet[0].ring_count, 2)
        self.assertEqual(fleet[0].ring_status, "multiple")
        self.assertEqual(
            fleet[0].ring_names,
            ("Ring A", "Ring B"),
        )

    def test_metrics_keep_ring_and_telemetry_planes_separate(self):
        now = datetime(2026, 9, 2, 2, 0, tzinfo=timezone.utc)
        states = [
            {
                "preRemediationDetectionScriptOutput":
                    "DEVICE=NEWER;LASTBOOT=2026-09-01T00:00:00Z;UPTIME_HOURS=26",
                "lastStateUpdateDateTime": "2026-09-02T01:30:00Z",
                "managedDevice": {
                    "deviceName": "NEWER",
                    "userPrincipalName": "n@example.com",
                },
            },
            {
                "preRemediationDetectionScriptOutput":
                    "DEVICE=OLDER;LASTBOOT=2026-08-20T00:00:00Z;UPTIME_HOURS=312",
                "lastStateUpdateDateTime": "2026-09-02T01:30:00Z",
                "managedDevice": {
                    "deviceName": "OLDER",
                    "userPrincipalName": "o@example.com",
                },
            },
        ]
        telemetry = parse_run_states(
            states,
            now=now,
            max_age_hours=48,
        )
        ring_reports = [
            RingReport(
                "NEWER",
                "n@example.com",
                "ring-a",
                "Ring A",
                "compliant",
                datetime(2026, 9, 2, 1, 40, tzinfo=timezone.utc),
            ),
            RingReport(
                "OLDER",
                "o@example.com",
                "ring-b",
                "Ring B",
                "compliant",
                datetime(2026, 9, 2, 1, 40, tzinfo=timezone.utc),
            ),
            RingReport(
                "MISSING",
                "m@example.com",
                "ring-a",
                "Ring A",
                "compliant",
                datetime(2026, 9, 2, 1, 40, tzinfo=timezone.utc),
            ),
        ]
        records = merge_fleet_devices(
            [
                ManagedWindowsDevice("NEWER", "n@example.com"),
                ManagedWindowsDevice("OLDER", "o@example.com"),
                ManagedWindowsDevice("MISSING", "m@example.com"),
                ManagedWindowsDevice("NO-RING", "x@example.com"),
            ],
            ring_reports,
            telemetry,
        )
        config = Config(
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
        metrics = build_metrics(
            records,
            config=config,
            now=now,
        )
        lines = metrics["intune.windows.top10"].splitlines()
        self.assertIn("OLDER", lines[2])
        self.assertIn("NEWER", lines[3])

        summary = json.loads(
            metrics["intune.windows.summary.json"]
        )
        self.assertEqual(summary["expected_devices"], 4)
        self.assertEqual(summary["ring_reporting_devices"], 3)
        self.assertEqual(summary["one_ring_devices"], 3)
        self.assertEqual(summary["no_ring_devices"], 1)
        self.assertEqual(summary["multiple_ring_devices"], 0)
        self.assertEqual(summary["reporting_devices"], 2)
        self.assertEqual(summary["missing_devices"], 2)

        limited_metrics = build_metrics(
            records,
            config=replace(config, top_n=1),
            now=now,
        )
        limited_summary = json.loads(
            limited_metrics["intune.windows.summary.json"]
        )
        self.assertEqual(len(limited_summary["devices"]), 4)
        self.assertEqual(len(limited_summary["top"]), 1)
        self.assertEqual(
            limited_summary["devices"][0]["computer_name"],
            "OLDER",
        )


if __name__ == "__main__":
    unittest.main()
