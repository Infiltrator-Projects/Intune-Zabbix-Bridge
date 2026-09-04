import unittest
from unittest.mock import patch

from intune_zabbix_bridge import current, hardened, ring_reports
from intune_zabbix_bridge.collector import Config, UpdateRing


class CurrentRingReportTests(unittest.TestCase):
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

    def test_schema_driven_rows_do_not_depend_on_column_position(self):
        rows = ring_reports.normalise_report_rows({
            "Schema": [
                {"Column": "DeviceName", "PropertyType": "String"},
                {"Column": "PolicyStatus", "PropertyType": "String"},
                {"Column": "IntuneDeviceId", "PropertyType": "String"},
            ],
            "Values": [["PC-A", "succeeded", "device-a"]],
        })
        self.assertEqual(rows, [{
            "DeviceName": "PC-A",
            "PolicyStatus": "succeeded",
            "IntuneDeviceId": "device-a",
        }])

    def test_report_fetch_pages_each_ring_and_annotates_rows(self):
        rings = [UpdateRing("ring-a", "Ring A"), UpdateRing("ring-b", "Ring B")]
        schema = [
            {"Column": "IntuneDeviceId"},
            {"Column": "DeviceName"},
            {"Column": "UPN"},
            {"Column": "PolicyStatus"},
            {"Column": "PspdpuLastModifiedTimeUtc"},
        ]
        replies = [
            {
                "Schema": schema,
                "Values": [
                    ["device-a", "PC-A", "a@example.com", "succeeded", "2026-09-04T01:00:00Z"],
                    ["device-b", "PC-B", "b@example.com", "succeeded", "2026-09-04T01:01:00Z"],
                ],
                "TotalRowCount": 3,
            },
            {
                "Schema": schema,
                "Values": [
                    ["device-c", "PC-C", "c@example.com", "pending", "2026-09-04T01:02:00Z"],
                ],
                "TotalRowCount": 3,
            },
            {
                "Schema": schema,
                "Values": [
                    ["device-d", "PC-D", "d@example.com", "succeeded", "2026-09-04T01:03:00Z"],
                ],
                "TotalRowCount": 1,
            },
        ]
        with patch.object(ring_reports, "REPORT_PAGE_SIZE", 2), \
             patch.object(ring_reports, "_post_report", side_effect=replies) as post:
            targets = ring_reports.fetch_ring_targets(self.config(), "token", rings)

        self.assertEqual(post.call_count, 3)
        self.assertEqual(
            [(row["_ring_name"], row["IntuneDeviceId"]) for row in targets],
            [
                ("Ring A", "device-a"),
                ("Ring A", "device-b"),
                ("Ring A", "device-c"),
                ("Ring B", "device-d"),
            ],
        )
        first_payload = post.call_args_list[0].args[2]
        second_payload = post.call_args_list[1].args[2]
        third_payload = post.call_args_list[2].args[2]
        self.assertEqual(first_payload["skip"], 0)
        self.assertEqual(second_payload["skip"], 2)
        self.assertEqual(third_payload["skip"], 0)
        self.assertIn("PolicyId eq 'ring-a'", first_payload["filter"])
        self.assertEqual(first_payload["select"], list(ring_reports.REPORT_COLUMNS))

    def test_intune_device_id_is_authoritative_ring_join(self):
        managed = [
            hardened.ManagedDevice("device-a", "SAME-PC", "a@example.com"),
            hardened.ManagedDevice("device-b", "SAME-PC", "b@example.com"),
        ]
        reports = ring_reports.parse_ring_targets(managed, [{
            "IntuneDeviceId": "device-b",
            "DeviceName": "SAME-PC",
            "UPN": "b@example.com",
            "PolicyStatus": "succeeded",
            "PspdpuLastModifiedTimeUtc": "2026-09-04T01:00:00Z",
            "_ring_id": "ring-a",
            "_ring_name": "Staff Ring",
        }])
        self.assertEqual(len(reports), 1)
        self.assertEqual(reports[0].managed_device_id, "device-b")
        self.assertEqual(reports[0].ring_name, "Staff Ring")
        self.assertEqual(reports[0].status, "succeeded")

    def test_ambiguous_name_fallback_never_guesses(self):
        managed = [
            hardened.ManagedDevice("device-a", "SAME-PC", "shared@example.com"),
            hardened.ManagedDevice("device-b", "SAME-PC", "shared@example.com"),
        ]
        reports = ring_reports.parse_ring_targets(managed, [{
            "DeviceName": "SAME-PC",
            "UPN": "shared@example.com",
            "PolicyStatus": "succeeded",
            "_ring_id": "ring-a",
            "_ring_name": "Ring A",
        }])
        self.assertEqual(reports, [])

    def test_duplicate_user_and_system_rows_collapse_to_newest_device_ring(self):
        managed = [hardened.ManagedDevice("device-a", "PC-A", "a@example.com")]
        reports = ring_reports.parse_ring_targets(managed, [
            {
                "IntuneDeviceId": "device-a",
                "DeviceName": "PC-A",
                "PolicyStatus": "pending",
                "PspdpuLastModifiedTimeUtc": "2026-09-04T00:30:00Z",
                "_ring_id": "ring-a",
                "_ring_name": "Ring A",
            },
            {
                "IntuneDeviceId": "device-a",
                "DeviceName": "PC-A",
                "PolicyStatus": "succeeded",
                "PspdpuLastModifiedTimeUtc": "2026-09-04T01:30:00Z",
                "_ring_id": "ring-a",
                "_ring_name": "Ring A",
            },
        ])
        self.assertEqual(len(reports), 1)
        self.assertEqual(reports[0].status, "succeeded")

    def test_shipped_entry_point_binds_current_report_source(self):
        old_fetch = hardened.fetch_ring_targets
        old_parse = hardened.parse_ring_targets
        try:
            current.install_current_ring_source()
            self.assertIs(hardened.fetch_ring_targets, ring_reports.fetch_ring_targets)
            self.assertIs(hardened.parse_ring_targets, ring_reports.parse_ring_targets)
        finally:
            hardened.fetch_ring_targets = old_fetch
            hardened.parse_ring_targets = old_parse


if __name__ == "__main__":
    unittest.main()
