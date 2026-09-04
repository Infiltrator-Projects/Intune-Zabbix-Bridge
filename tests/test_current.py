import json
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from intune_zabbix_bridge import current, hardened
from intune_zabbix_bridge.collector import Config


class CurrentRuntimeTests(unittest.TestCase):
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

    @staticmethod
    def state(device_id: str, name: str, collected: str) -> dict:
        return {
            "preRemediationDetectionScriptOutput": (
                f"DEVICE={name};LASTBOOT=2026-09-03T00:00:00Z;UPTIME_HOURS=30"
            ),
            "lastStateUpdateDateTime": collected,
            "managedDevice": {
                "id": device_id,
                "deviceName": name,
                "userPrincipalName": f"{name.lower()}@example.com",
            },
        }

    def test_operational_population_is_devices_with_reboot_telemetry(self):
        states = [
            self.state("device-a", "PC-A", "2026-09-04T01:50:00Z"),
            self.state("device-b", "PC-B", "2026-09-04T01:40:00Z"),
        ]
        fixed_now = datetime(2026, 9, 4, 2, 0, tzinfo=timezone.utc)

        with patch.object(current.legacy, "get_access_token", return_value="token"), \
             patch.object(current.legacy, "fetch_run_states", return_value=states), \
             patch.object(current, "datetime") as mocked_datetime:
            mocked_datetime.now.return_value = fixed_now
            records, metrics = current.collect_telemetry_only(self.config())

        self.assertEqual(len(records), 2)
        self.assertTrue(all(record.telemetry_status == "fresh" for record in records))
        summary = json.loads(metrics[hardened.SUMMARY_KEY])
        self.assertEqual(summary["expected_devices"], 2)
        self.assertEqual(summary["reporting_devices"], 2)
        self.assertEqual(summary["fresh_devices"], 2)
        self.assertEqual(summary["missing_devices"], 0)

    def test_publication_uses_only_original_template_companion_keys(self):
        metrics = {
            "intune.windows.reporting.count": "2",
            "intune.windows.fresh.count": "2",
            "intune.windows.stale.count": "0",
            "intune.windows.ring.reporting.count": "0",
            "intune.windows.ring.one.count": "0",
            "intune.windows.ring.none.count": "2",
            "intune.windows.ring.multiple.count": "0",
            "intune.windows.reboot.missed.count": "0",
            "intune.windows.reboot.current.count": "0",
            "intune.windows.reboot.unknown.count": "0",
            "intune.windows.reboot.notactive.count": "2",
            "intune.windows.max.uptime.days": "10.000",
            "intune.windows.uptime.over7.count": "1",
            "intune.windows.uptime.over14.count": "0",
            "intune.windows.uptime.over30.count": "0",
            "intune.windows.last.collection.epoch": "1",
            "intune.windows.top10": "table",
            hardened.SUMMARY_KEY: "{}",
        }

        filtered = current.baseline_zabbix_metrics(metrics)
        self.assertEqual(set(filtered), set(current._BASELINE_ZABBIX_KEYS))
        self.assertNotIn("intune.windows.ring.reporting.count", filtered)
        self.assertNotIn("intune.windows.reboot.notactive.count", filtered)
        self.assertIn(hardened.SUMMARY_KEY, filtered)

    def test_zero_usable_telemetry_keeps_last_known_good_generation(self):
        with patch.object(current.legacy, "get_access_token", return_value="token"), \
             patch.object(current.legacy, "fetch_run_states", return_value=[]):
            with self.assertRaisesRegex(RuntimeError, "zero usable reboot telemetry"):
                current.collect_telemetry_only(self.config())


if __name__ == "__main__":
    unittest.main()
