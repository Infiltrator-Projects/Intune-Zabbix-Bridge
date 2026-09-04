import json
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from intune_zabbix_bridge import hardened
from intune_zabbix_bridge.collector import Config, UpdateRing


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
                "azureADDeviceId": "aad-a",
                "deviceName": "SAME-PC",
                "userPrincipalName": "a@example.com",
                "operatingSystem": "Windows",
                "lastSyncDateTime": "2026-09-04T00:00:00Z",
            },
            {
                "id": "device-b",
                "azureADDeviceId": "aad-b",
                "deviceName": "SAME-PC",
                "userPrincipalName": "b@example.com",
                "operatingSystem": "Windows",
                "lastSyncDateTime": "2026-09-04T00:01:00Z",
            },
        ])
        self.assertEqual(len(rows), 2)
        self.assertEqual(
            {row.managed_device_id for row in rows},
            {"device-a", "device-b"},
        )

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

    def test_ring_target_uses_immutable_managed_device_id(self):
        managed = [
            hardened.ManagedDevice("device-a", "SAME-PC", "a@example.com", "aad-a"),
            hardened.ManagedDevice("device-b", "SAME-PC", "b@example.com", "aad-b"),
        ]
        reports = hardened.parse_ring_targets(managed, [{
            "deviceId": "device-b",
            "deviceName": "SAME-PC",
            "userPrincipalName": "b@example.com",
            "lastCheckinDateTime": "2026-09-04T01:00:00Z",
            "_ring_id": "ring-a",
            "_ring_name": "Ring A",
        }])
        self.assertEqual(len(reports), 1)
        self.assertEqual(reports[0].managed_device_id, "device-b")
        self.assertEqual(reports[0].ring_name, "Ring A")
        self.assertEqual(reports[0].status, "targeted")

    def test_ring_target_can_map_azure_ad_device_id(self):
        managed = [
            hardened.ManagedDevice("device-a", "PC-A", "a@example.com", "aad-a"),
        ]
        reports = hardened.parse_ring_targets(managed, [{
            "deviceId": "AAD-A",
            "deviceName": "PC-A",
            "userPrincipalName": "a@example.com",
            "_ring_id": "ring-a",
            "_ring_name": "Ring A",
        }])
        self.assertEqual(len(reports), 1)
        self.assertEqual(reports[0].managed_device_id, "device-a")

    def test_ambiguous_target_does_not_guess_by_hostname(self):
        managed = [
            hardened.ManagedDevice("device-a", "SAME-PC", "shared@example.com"),
            hardened.ManagedDevice("device-b", "SAME-PC", "shared@example.com"),
        ]
        reports = hardened.parse_ring_targets(managed, [{
            "deviceId": "unknown-id",
            "deviceName": "SAME-PC",
            "userPrincipalName": "shared@example.com",
            "_ring_id": "ring-a",
            "_ring_name": "Ring A",
        }])
        self.assertEqual(reports, [])

    def test_targeting_fetches_each_ring_and_annotates_membership(self):
        rings = [
            UpdateRing("ring-a", "Ring A"),
            UpdateRing("ring-b", "Ring B"),
            UpdateRing("ring-c", "Ring C"),
        ]
        replies = [
            {"value": [{"deviceId": "device-a", "deviceName": "PC-A"}]},
            {"value": [{"deviceId": "device-b", "deviceName": "PC-B"}]},
            {"value": [{"deviceId": "device-c", "deviceName": "PC-C"}]},
        ]
        with patch.object(hardened, "_graph_post", side_effect=replies) as post:
            targets = hardened.fetch_ring_targets(self.config(), "token", rings)

        self.assertEqual(post.call_count, 3)
        self.assertEqual(
            {(t["_ring_id"], t["_ring_name"], t["deviceId"]) for t in targets},
            {
                ("ring-a", "Ring A", "device-a"),
                ("ring-b", "Ring B", "device-b"),
                ("ring-c", "Ring C", "device-c"),
            },
        )
        for call, ring in zip(post.call_args_list, rings):
            self.assertEqual(
                call.args[3],
                {"deviceConfigurationIds": [ring.ring_id]},
            )
            self.assertIn("getTargetedUsersAndDevices", call.args[2])

    def test_multiple_targeted_rings_remain_visible_as_fault(self):
        managed = [
            hardened.ManagedDevice("device-a", "PC-A", "a@example.com"),
        ]
        reports = hardened.parse_ring_targets(managed, [
            {
                "deviceId": "device-a",
                "_ring_id": "ring-a",
                "_ring_name": "Ring A",
            },
            {
                "deviceId": "device-a",
                "_ring_id": "ring-b",
                "_ring_name": "Ring B",
            },
        ])
        fleet = hardened.merge_fleet_devices(managed, reports, [])
        self.assertEqual(fleet[0].ring_count, 2)
        self.assertEqual(fleet[0].ring_state, "multiple")
        self.assertEqual(fleet[0].ring_names, ("Ring A", "Ring B"))

    def test_metrics_do_not_collapse_duplicate_hostnames(self):
        now = datetime(2026, 9, 4, 2, 0, tzinfo=timezone.utc)
        records = [
            hardened.FleetDevice(
                "device-a", "SAME-PC", "a@example.com", (), 0, "none",
                "not-targeted", None, None, None, None, None, "missing"
            ),
            hardened.FleetDevice(
                "device-b", "SAME-PC", "b@example.com", (), 0, "none",
                "not-targeted", None, None, None, None, None, "missing"
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

    def test_zero_resolvable_ring_targets_fails_closed(self):
        managed = [{
            "id": "device-a",
            "deviceName": "PC-A",
            "userPrincipalName": "a@example.com",
            "operatingSystem": "Windows",
        }]
        rings = [UpdateRing("ring-a", "Ring A")]
        with patch.object(hardened.legacy, "get_access_token", return_value="token"), \
             patch.object(hardened, "fetch_managed_windows_devices", return_value=managed), \
             patch.object(hardened.legacy, "fetch_update_rings", return_value=rings), \
             patch.object(hardened, "fetch_ring_targets", return_value=[]):
            with self.assertRaisesRegex(RuntimeError, "no resolvable targeted Windows devices"):
                hardened.collect(self.config())


if __name__ == "__main__":
    unittest.main()
