import json
import unittest
from dataclasses import replace
from datetime import datetime, timezone

from intune_zabbix_bridge.collector import (
    Config,
    build_metrics,
    parse_datetime,
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
        records = parse_run_states(states, now=now, max_age_hours=48)
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
        self.assertEqual(len(summary["devices"]), 2)
        self.assertEqual(len(summary["top"]), 1)
        self.assertEqual(summary["devices"][0]["computer_name"], "OLDER")


if __name__ == "__main__":
    unittest.main()
