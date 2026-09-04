#!/usr/bin/env python3
"""Hardened Intune -> Zabbix collector.

The collector keeps three planes of truth separate:

* managedDevice.id is the authoritative fleet identity;
* Windows Update Ring membership comes from Intune's current targeting action,
  not the deprecated deviceConfigurationDeviceStatus feed;
* reboot telemetry joins only by expanded managedDevice.id.

The dashboard summary is published last and acts as the generation commit marker.
"""

from __future__ import annotations

import json
import logging
import subprocess
import sys
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable
from zoneinfo import ZoneInfo

from . import collector as legacy

LOG = logging.getLogger("intune-zabbix-bridge")
SUMMARY_KEY = "intune.windows.summary.json"


@dataclass(frozen=True)
class ManagedDevice:
    managed_device_id: str
    computer_name: str
    user: str
    azure_ad_device_id: str = ""
    last_sync: datetime | None = None


@dataclass(frozen=True)
class DeviceTelemetry:
    managed_device_id: str
    computer_name: str
    user: str
    last_restart: datetime
    telemetry_collected: datetime
    uptime_days: float
    telemetry_age_hours: float
    fresh: bool


@dataclass(frozen=True)
class RingReport:
    managed_device_id: str
    computer_name: str
    user: str
    ring_id: str
    ring_name: str
    status: str
    last_reported: datetime | None


@dataclass(frozen=True)
class FleetDevice:
    managed_device_id: str
    computer_name: str
    user: str
    ring_names: tuple[str, ...]
    ring_count: int
    ring_state: str
    ring_status: str
    ring_last_reported: datetime | None
    last_restart: datetime | None
    telemetry_collected: datetime | None
    uptime_days: float | None
    telemetry_age_hours: float | None
    telemetry_status: str

    @property
    def fresh(self) -> bool:
        return self.telemetry_status == "fresh"

    def as_json(
        self,
        local_tz: ZoneInfo,
        reboot: legacy.RebootRequirement,
    ) -> dict[str, Any]:
        return {
            "managed_device_id": self.managed_device_id,
            "computer_name": self.computer_name,
            "user": self.user,
            "ring_name": "; ".join(self.ring_names),
            "ring_count": self.ring_count,
            "ring_state": self.ring_state,
            "ring_status": self.ring_status,
            "ring_last_reported": (
                self.ring_last_reported.astimezone(local_tz).isoformat()
                if self.ring_last_reported is not None
                else ""
            ),
            "last_restart": (
                self.last_restart.astimezone(local_tz).isoformat()
                if self.last_restart is not None
                else ""
            ),
            "telemetry_collected": (
                self.telemetry_collected.astimezone(local_tz).isoformat()
                if self.telemetry_collected is not None
                else ""
            ),
            "uptime_days": round(self.uptime_days, 3) if self.uptime_days is not None else None,
            "telemetry_age_hours": (
                round(self.telemetry_age_hours, 2)
                if self.telemetry_age_hours is not None
                else None
            ),
            "fresh": self.fresh,
            "telemetry_status": self.telemetry_status,
            "reboot_state": reboot.state,
            "reboot_priority": reboot.priority,
            "reboot_due": (
                reboot.due_at.astimezone(local_tz).isoformat()
                if reboot.due_at is not None
                else ""
            ),
        }


def fetch_managed_windows_devices(
    config: legacy.Config,
    token: str,
) -> list[dict[str, Any]]:
    url = (
        f"{legacy.GRAPH_V1_ROOT}/deviceManagement/managedDevices"
        "?$top=999&$select=id,deviceName,userPrincipalName,operatingSystem,"
        "azureADDeviceId,lastSyncDateTime"
    )
    return legacy.graph_get_all(config, token, url)


def parse_managed_windows_devices(
    devices: Iterable[dict[str, Any]],
) -> list[ManagedDevice]:
    newest_by_id: dict[str, ManagedDevice] = {}

    for device in devices:
        if str(device.get("operatingSystem") or "").casefold() != "windows":
            continue

        managed_device_id = str(device.get("id") or "").strip()
        computer_name = str(device.get("deviceName") or "").strip()
        if not managed_device_id or not computer_name:
            continue

        last_sync_raw = str(device.get("lastSyncDateTime") or "").strip()
        last_sync: datetime | None = None
        if last_sync_raw:
            try:
                last_sync = legacy.parse_datetime(last_sync_raw)
            except (TypeError, ValueError):
                LOG.warning("Ignoring malformed Intune last-sync time for %s", computer_name)

        record = ManagedDevice(
            managed_device_id=managed_device_id,
            computer_name=computer_name,
            user=str(device.get("userPrincipalName") or "").strip(),
            azure_ad_device_id=str(device.get("azureADDeviceId") or "").strip(),
            last_sync=last_sync,
        )
        key = managed_device_id.casefold()
        existing = newest_by_id.get(key)
        if existing is None or (
            record.last_sync is not None
            and (existing.last_sync is None or record.last_sync > existing.last_sync)
        ):
            newest_by_id[key] = record

    return list(newest_by_id.values())


def parse_run_states(
    states: Iterable[dict[str, Any]],
    *,
    now: datetime,
    max_age_hours: float,
) -> list[DeviceTelemetry]:
    newest_by_id: dict[str, DeviceTelemetry] = {}

    for state in states:
        output = str(state.get("preRemediationDetectionScriptOutput") or "")
        match = legacy.TELEMETRY_RE.search(output)
        if not match:
            continue

        managed = state.get("managedDevice") or {}
        managed_device_id = str(managed.get("id") or "").strip()
        computer_name = str(managed.get("deviceName") or match.group("device") or "").strip()
        if not managed_device_id or not computer_name:
            LOG.warning("Skipping reboot telemetry without immutable managedDevice.id")
            continue

        collected_raw = str(state.get("lastStateUpdateDateTime") or "").strip()
        if not collected_raw:
            continue

        try:
            last_restart = legacy.parse_datetime(match.group("lastboot"))
            collected = legacy.parse_datetime(collected_raw)
        except (TypeError, ValueError):
            LOG.warning("Skipping malformed telemetry for %s", computer_name)
            continue

        uptime_days = max(0.0, (now - last_restart).total_seconds() / 86400.0)
        age_hours = max(0.0, (now - collected).total_seconds() / 3600.0)
        record = DeviceTelemetry(
            managed_device_id=managed_device_id,
            computer_name=computer_name,
            user=str(managed.get("userPrincipalName") or "").strip(),
            last_restart=last_restart,
            telemetry_collected=collected,
            uptime_days=uptime_days,
            telemetry_age_hours=age_hours,
            fresh=age_hours <= max_age_hours,
        )

        key = managed_device_id.casefold()
        existing = newest_by_id.get(key)
        if existing is None or record.telemetry_collected > existing.telemetry_collected:
            newest_by_id[key] = record

    return list(newest_by_id.values())


def _graph_post(
    config: legacy.Config,
    token: str,
    url: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
    )
    return legacy._request_json(
        request,
        timeout=config.http_timeout,
        retries=config.http_retries,
    )


def fetch_ring_targets(
    config: legacy.Config,
    token: str,
    rings: Iterable[legacy.UpdateRing],
) -> list[dict[str, Any]]:
    """Fetch effective targets for each update ring.

    Intune's deviceConfigurationDeviceStatus entity is deprecated. Ring
    membership is an assignment/targeting question, so this uses
    getTargetedUsersAndDevices once per ring and annotates each returned target
    with the authoritative ring id/name.
    """
    endpoint = (
        f"{legacy.GRAPH_BETA_ROOT}/deviceManagement/deviceConfigurations/"
        "getTargetedUsersAndDevices"
    )
    targets: list[dict[str, Any]] = []

    for ring in rings:
        page = _graph_post(
            config,
            token,
            endpoint,
            {"deviceConfigurationIds": [ring.ring_id]},
        )
        while True:
            values = page.get("value", [])
            if not isinstance(values, list):
                raise RuntimeError(
                    f"Intune targeting response for {ring.display_name} did not contain a list."
                )
            for item in values:
                if not isinstance(item, dict):
                    continue
                target = dict(item)
                target["_ring_id"] = ring.ring_id
                target["_ring_name"] = ring.display_name
                targets.append(target)

            next_link = str(page.get("@odata.nextLink") or "").strip()
            if not next_link:
                break
            page = legacy.graph_get(config, token, next_link)

    return targets


def _identity_maps(
    managed_devices: Iterable[ManagedDevice],
) -> tuple[
    dict[str, str],
    dict[str, str],
    dict[tuple[str, str], str],
    dict[str, str],
]:
    by_managed_id: dict[str, str] = {}
    by_aad_id_candidates: dict[str, set[str]] = {}
    by_name_user_candidates: dict[tuple[str, str], set[str]] = {}
    by_name_candidates: dict[str, set[str]] = {}

    for device in managed_devices:
        device_id = device.managed_device_id
        by_managed_id[device_id.casefold()] = device_id

        aad_id = device.azure_ad_device_id.casefold()
        if aad_id:
            by_aad_id_candidates.setdefault(aad_id, set()).add(device_id)

        name = device.computer_name.casefold()
        user = device.user.casefold()
        by_name_candidates.setdefault(name, set()).add(device_id)
        if user:
            by_name_user_candidates.setdefault((name, user), set()).add(device_id)

    by_aad_id = {
        key: next(iter(ids))
        for key, ids in by_aad_id_candidates.items()
        if len(ids) == 1
    }
    by_name_user = {
        key: next(iter(ids))
        for key, ids in by_name_user_candidates.items()
        if len(ids) == 1
    }
    by_name = {
        key: next(iter(ids))
        for key, ids in by_name_candidates.items()
        if len(ids) == 1
    }
    return by_managed_id, by_aad_id, by_name_user, by_name


def parse_ring_targets(
    managed_devices: list[ManagedDevice],
    targets: Iterable[dict[str, Any]],
) -> list[RingReport]:
    by_managed_id, by_aad_id, by_name_user, by_name = _identity_maps(managed_devices)
    managed_by_id = {d.managed_device_id.casefold(): d for d in managed_devices}
    newest_by_device_ring: dict[tuple[str, str], RingReport] = {}

    for target in targets:
        ring_id = str(target.get("_ring_id") or "").strip()
        ring_name = str(target.get("_ring_name") or "").strip()
        if not ring_id or not ring_name:
            continue

        target_id = str(target.get("deviceId") or "").strip().casefold()
        target_name = str(target.get("deviceName") or "").strip()
        target_user = str(target.get("userPrincipalName") or "").strip()

        managed_device_id = by_managed_id.get(target_id) if target_id else None
        if managed_device_id is None and target_id:
            managed_device_id = by_aad_id.get(target_id)

        if managed_device_id is None and target_name and target_user:
            managed_device_id = by_name_user.get(
                (target_name.casefold(), target_user.casefold())
            )
        if managed_device_id is None and target_name:
            managed_device_id = by_name.get(target_name.casefold())

        if managed_device_id is None:
            LOG.warning(
                "Not attaching unresolved update-ring target %s / %s (deviceId=%s)",
                target_name or "<unnamed>",
                ring_name,
                target_id or "<none>",
            )
            continue

        managed = managed_by_id[managed_device_id.casefold()]
        last_checkin_raw = str(target.get("lastCheckinDateTime") or "").strip()
        last_checkin: datetime | None = None
        if last_checkin_raw:
            try:
                last_checkin = legacy.parse_datetime(last_checkin_raw)
            except (TypeError, ValueError):
                LOG.warning(
                    "Ignoring malformed ring targeting check-in for %s / %s",
                    managed.computer_name,
                    ring_name,
                )

        record = RingReport(
            managed_device_id=managed_device_id,
            computer_name=managed.computer_name,
            user=target_user or managed.user,
            ring_id=ring_id,
            ring_name=ring_name,
            status="targeted",
            last_reported=last_checkin,
        )
        key = (managed_device_id.casefold(), ring_id.casefold())
        existing = newest_by_device_ring.get(key)
        if existing is None or (
            record.last_reported is not None
            and (
                existing.last_reported is None
                or record.last_reported > existing.last_reported
            )
        ):
            newest_by_device_ring[key] = record

    return list(newest_by_device_ring.values())


def merge_fleet_devices(
    managed_devices: Iterable[ManagedDevice],
    ring_reports: Iterable[RingReport],
    telemetry_records: Iterable[DeviceTelemetry],
) -> list[FleetDevice]:
    telemetry_by_id = {
        record.managed_device_id.casefold(): record for record in telemetry_records
    }
    rings_by_id: dict[str, list[RingReport]] = {}
    for report in ring_reports:
        rings_by_id.setdefault(report.managed_device_id.casefold(), []).append(report)

    fleet: list[FleetDevice] = []
    for managed in managed_devices:
        key = managed.managed_device_id.casefold()
        reports = sorted(
            rings_by_id.get(key, []),
            key=lambda report: report.ring_name.casefold(),
        )
        ring_names = tuple(report.ring_name for report in reports)
        ring_count = len(ring_names)

        if ring_count == 0:
            ring_state = "none"
            ring_status = "not-targeted"
            ring_last_reported = None
            ring_user = ""
        elif ring_count == 1:
            ring_state = "one"
            ring_status = reports[0].status
            ring_last_reported = reports[0].last_reported
            ring_user = reports[0].user
        else:
            ring_state = "multiple"
            ring_status = "multiple"
            ring_last_reported = max(
                (report.last_reported for report in reports if report.last_reported is not None),
                default=None,
            )
            ring_user = next((report.user for report in reports if report.user), "")

        telemetry = telemetry_by_id.get(key)
        fleet.append(FleetDevice(
            managed_device_id=managed.managed_device_id,
            computer_name=managed.computer_name,
            user=(telemetry.user if telemetry else "") or managed.user or ring_user,
            ring_names=ring_names,
            ring_count=ring_count,
            ring_state=ring_state,
            ring_status=ring_status,
            ring_last_reported=ring_last_reported,
            last_restart=telemetry.last_restart if telemetry else None,
            telemetry_collected=telemetry.telemetry_collected if telemetry else None,
            uptime_days=telemetry.uptime_days if telemetry else None,
            telemetry_age_hours=telemetry.telemetry_age_hours if telemetry else None,
            telemetry_status=("fresh" if telemetry and telemetry.fresh else "stale")
            if telemetry else "missing",
        ))

    return fleet


def build_metrics(
    records: list[FleetDevice],
    *,
    config: legacy.Config,
    now: datetime,
) -> dict[str, str]:
    local_tz = ZoneInfo(config.timezone_name)
    telemetry_reporting = [r for r in records if r.telemetry_status != "missing"]
    fresh = [r for r in records if r.telemetry_status == "fresh"]
    stale = [r for r in records if r.telemetry_status == "stale"]
    missing = [r for r in records if r.telemetry_status == "missing"]
    ring_reporting = [r for r in records if r.ring_count >= 1]
    one_ring = [r for r in records if r.ring_count == 1]
    no_ring = [r for r in records if r.ring_count == 0]
    multiple_ring = [r for r in records if r.ring_count > 1]

    latest_collection = max(
        (r.telemetry_collected for r in telemetry_reporting if r.telemetry_collected is not None),
        default=None,
    )
    max_uptime = max(
        (r.uptime_days for r in fresh if r.uptime_days is not None),
        default=0.0,
    )

    reboot_by_id = {
        r.managed_device_id.casefold(): legacy.evaluate_reboot_requirement(
            r, config=config, now=now
        )
        for r in records
    }

    def state_count(state: str) -> int:
        return sum(
            reboot_by_id[r.managed_device_id.casefold()].state == state for r in records
        )

    ranked = sorted(
        records,
        key=lambda r: (
            reboot_by_id[r.managed_device_id.casefold()].priority,
            r.uptime_days if r.uptime_days is not None else -1.0,
        ),
        reverse=True,
    )
    serialised = [
        r.as_json(local_tz, reboot_by_id[r.managed_device_id.casefold()]) for r in ranked
    ]
    ranked_fresh = [r for r in ranked if r.telemetry_status == "fresh"]

    summary = {
        "generated_at": now.astimezone(local_tz).isoformat(),
        "expected_devices": len(records),
        "ring_reporting_devices": len(ring_reporting),
        "one_ring_devices": len(one_ring),
        "no_ring_devices": len(no_ring),
        "multiple_ring_devices": len(multiple_ring),
        "reporting_devices": len(telemetry_reporting),
        "fresh_devices": len(fresh),
        "stale_devices": len(stale),
        "missing_devices": len(missing),
        "reboot_missed_devices": state_count("missed"),
        "reboot_current_devices": state_count("current"),
        "reboot_unknown_devices": state_count("unknown"),
        "reboot_not_active_devices": state_count("not-active"),
        "weekly_restart_day": config.weekly_restart_day,
        "weekly_restart_time": config.weekly_restart_time,
        "weekly_restart_policy_start": config.weekly_restart_policy_start,
        "max_telemetry_age_hours": config.max_telemetry_age_hours,
        "max_uptime_days": round(max_uptime, 3),
        "over_7_days": sum((r.uptime_days or 0.0) >= 7 for r in fresh),
        "over_14_days": sum((r.uptime_days or 0.0) >= 14 for r in fresh),
        "over_30_days": sum((r.uptime_days or 0.0) >= 30 for r in fresh),
        "devices": serialised,
        "top": [
            r.as_json(local_tz, reboot_by_id[r.managed_device_id.casefold()])
            for r in ranked_fresh[: config.top_n]
        ],
    }

    return {
        "intune.windows.reporting.count": str(len(telemetry_reporting)),
        "intune.windows.fresh.count": str(len(fresh)),
        "intune.windows.stale.count": str(len(stale)),
        "intune.windows.ring.reporting.count": str(len(ring_reporting)),
        "intune.windows.ring.one.count": str(len(one_ring)),
        "intune.windows.ring.none.count": str(len(no_ring)),
        "intune.windows.ring.multiple.count": str(len(multiple_ring)),
        "intune.windows.reboot.missed.count": str(state_count("missed")),
        "intune.windows.reboot.current.count": str(state_count("current")),
        "intune.windows.reboot.unknown.count": str(state_count("unknown")),
        "intune.windows.reboot.notactive.count": str(state_count("not-active")),
        "intune.windows.max.uptime.days": f"{max_uptime:.3f}",
        "intune.windows.uptime.over7.count": str(sum((r.uptime_days or 0.0) >= 7 for r in fresh)),
        "intune.windows.uptime.over14.count": str(sum((r.uptime_days or 0.0) >= 14 for r in fresh)),
        "intune.windows.uptime.over30.count": str(sum((r.uptime_days or 0.0) >= 30 for r in fresh)),
        "intune.windows.last.collection.epoch": str(
            int(latest_collection.timestamp()) if latest_collection else 0
        ),
        "intune.windows.top10": legacy.build_top_table(
            records, top_n=config.top_n, local_tz=local_tz
        ),
        SUMMARY_KEY: json.dumps(summary, separators=(",", ":")),
    }


def _send_metric(config: legacy.Config, key: str, value: str) -> None:
    completed = subprocess.run(
        [
            config.zabbix_sender,
            "-z", config.zabbix_server,
            "-p", str(config.zabbix_port),
            "-s", config.zabbix_host,
            "-k", key,
            "-o", value,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"zabbix_sender failure for {key}: {completed.stdout.strip()}"
        )


def send_metrics(
    config: legacy.Config,
    metrics: dict[str, str],
    *,
    sender: Any | None = None,
) -> None:
    send_one = sender or _send_metric

    for key, value in metrics.items():
        if key == SUMMARY_KEY:
            continue
        send_one(config, key, value)

    if SUMMARY_KEY not in metrics:
        raise RuntimeError("summary metric is missing from generated metrics")
    send_one(config, SUMMARY_KEY, metrics[SUMMARY_KEY])


def collect(config: legacy.Config) -> tuple[list[FleetDevice], dict[str, str]]:
    now = datetime.now(timezone.utc)
    token = legacy.get_access_token(config)

    managed_devices = parse_managed_windows_devices(
        fetch_managed_windows_devices(config, token)
    )
    if not managed_devices:
        raise RuntimeError(
            "Microsoft Graph returned zero managed Windows devices; "
            "refusing to publish an empty fleet."
        )

    rings = legacy.fetch_update_rings(config, token)
    raw_ring_targets = fetch_ring_targets(config, token, rings)
    ring_reports = parse_ring_targets(managed_devices, raw_ring_targets)
    if not ring_reports:
        raise RuntimeError(
            "Intune returned update rings but no resolvable targeted Windows devices; "
            "refusing to publish a misleading all-unassigned fleet."
        )

    raw_states = legacy.fetch_run_states(config, token)
    telemetry_records = parse_run_states(
        raw_states,
        now=now,
        max_age_hours=config.max_telemetry_age_hours,
    )
    records = merge_fleet_devices(managed_devices, ring_reports, telemetry_records)
    return records, build_metrics(records, config=config, now=now)


def main(argv: list[str] | None = None) -> int:
    args = legacy.parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)s %(message)s",
    )

    try:
        config = legacy.Config.from_env()
        records, metrics = collect(config)
        summary = json.loads(metrics[SUMMARY_KEY])
        LOG.info(
            "Fleet %d Windows devices (%d one ring, %d no ring, %d multiple rings; "
            "%d telemetry reporting, %d fresh, %d stale, %d missing; "
            "%d missed reboot, %d current, %d unknown, %d not active)",
            summary["expected_devices"],
            summary["one_ring_devices"],
            summary["no_ring_devices"],
            summary["multiple_ring_devices"],
            summary["reporting_devices"],
            summary["fresh_devices"],
            summary["stale_devices"],
            summary["missing_devices"],
            summary["reboot_missed_devices"],
            summary["reboot_current_devices"],
            summary["reboot_unknown_devices"],
            summary["reboot_not_active_devices"],
        )

        if args.dry_run:
            print(
                metrics[SUMMARY_KEY]
                if args.json_output
                else metrics["intune.windows.top10"]
            )
            return 0

        send_metrics(config, metrics)
        LOG.info("Published %d Zabbix items", len(metrics))
        return 0
    except Exception as exc:
        LOG.error("%s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
