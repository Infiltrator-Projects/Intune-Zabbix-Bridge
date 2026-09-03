#!/usr/bin/env python3
"""Microsoft Intune -> Zabbix reboot telemetry bridge.

The bridge is deliberately read-only against Microsoft Graph.

Reboot Watch keeps three separate planes of truth:

1. the current Intune managed-Windows inventory defines the estate that must
   never silently disappear;
2. Windows Update Ring deviceStatuses prove which update-ring configuration(s)
   each device has actually reported to Intune;
3. the existing Intune Remediation / deviceHealthScript reports actual Windows
   boot telemetry in this format:

       DEVICE=<name>;LASTBOOT=<ISO-8601>;UPTIME_HOURS=<number>

A current Windows device with no ring status, multiple ring statuses, stale
telemetry or no telemetry remains visible as an explicit fault state. The
bridge publishes fleet-level metrics to a single Zabbix host using
zabbix_sender. No connection to managed laptops is required.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, time as dt_time, timedelta, timezone
from typing import Any, Iterable
from zoneinfo import ZoneInfo

LOG = logging.getLogger("intune-zabbix-bridge")

GRAPH_BETA_ROOT = "https://graph.microsoft.com/beta"
GRAPH_V1_ROOT = "https://graph.microsoft.com/v1.0"
TOKEN_SCOPE = "https://graph.microsoft.com/.default"
TELEMETRY_RE = re.compile(
    r"(?:^|;)DEVICE=(?P<device>[^;]+);LASTBOOT=(?P<lastboot>[^;]+);"
    r"UPTIME_HOURS=(?P<uptime>[0-9.]+)(?:;|$)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Config:
    tenant_id: str
    client_id: str
    client_secret: str
    telemetry_script_id: str
    zabbix_server: str
    zabbix_port: int
    zabbix_host: str
    zabbix_sender: str
    timezone_name: str
    max_telemetry_age_hours: float
    top_n: int
    http_timeout: float
    http_retries: int
    weekly_restart_day: str = "sunday"
    weekly_restart_time: str = "03:00"
    weekly_restart_policy_start: str = "2026-09-06T03:00:00"

    @classmethod
    def from_env(cls) -> "Config":
        required = {
            "AZURE_TENANT_ID": os.getenv("AZURE_TENANT_ID", "").strip(),
            "AZURE_CLIENT_ID": os.getenv("AZURE_CLIENT_ID", "").strip(),
            "AZURE_CLIENT_SECRET": os.getenv("AZURE_CLIENT_SECRET", "").strip(),
            "INTUNE_TELEMETRY_SCRIPT_ID": os.getenv(
                "INTUNE_TELEMETRY_SCRIPT_ID", ""
            ).strip(),
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise ValueError(
                "Missing required environment variable(s): " + ", ".join(missing)
            )

        return cls(
            tenant_id=required["AZURE_TENANT_ID"],
            client_id=required["AZURE_CLIENT_ID"],
            client_secret=required["AZURE_CLIENT_SECRET"],
            telemetry_script_id=required["INTUNE_TELEMETRY_SCRIPT_ID"],
            zabbix_server=os.getenv("ZABBIX_SERVER", "127.0.0.1").strip(),
            zabbix_port=int(os.getenv("ZABBIX_PORT", "10051")),
            zabbix_host=os.getenv(
                "ZABBIX_HOST", "Microsoft Intune - Windows Fleet"
            ).strip(),
            zabbix_sender=os.getenv("ZABBIX_SENDER", "zabbix_sender").strip(),
            timezone_name=os.getenv("TIMEZONE", "Australia/Melbourne").strip(),
            max_telemetry_age_hours=float(
                os.getenv("MAX_TELEMETRY_AGE_HOURS", "48")
            ),
            top_n=max(1, int(os.getenv("TOP_N", "10"))),
            http_timeout=float(os.getenv("HTTP_TIMEOUT_SECONDS", "20")),
            http_retries=max(0, int(os.getenv("HTTP_RETRIES", "4"))),
            weekly_restart_day=os.getenv(
                "WEEKLY_RESTART_DAY", "sunday"
            ).strip().lower(),
            weekly_restart_time=os.getenv(
                "WEEKLY_RESTART_TIME", "03:00"
            ).strip(),
            weekly_restart_policy_start=os.getenv(
                "WEEKLY_RESTART_POLICY_START",
                "2026-09-06T03:00:00",
            ).strip(),
        )


@dataclass(frozen=True)
class DeviceTelemetry:
    computer_name: str
    user: str
    last_restart: datetime
    telemetry_collected: datetime
    uptime_days: float
    telemetry_age_hours: float
    fresh: bool


@dataclass(frozen=True)
class ManagedWindowsDevice:
    computer_name: str
    user: str
    last_sync: datetime | None = None


@dataclass(frozen=True)
class UpdateRing:
    ring_id: str
    display_name: str


@dataclass(frozen=True)
class RingReport:
    computer_name: str
    user: str
    ring_id: str
    ring_name: str
    status: str
    last_reported: datetime | None


@dataclass(frozen=True)
class RebootRequirement:
    state: str
    due_at: datetime | None
    priority: int


@dataclass(frozen=True)
class FleetDevice:
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
        reboot: RebootRequirement,
    ) -> dict[str, Any]:
        return {
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
            "uptime_days": (
                round(self.uptime_days, 3)
                if self.uptime_days is not None
                else None
            ),
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


WEEKDAYS = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


def parse_datetime(value: str) -> datetime:
    value = value.strip()
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _restart_schedule(config: Config) -> tuple[ZoneInfo, int, dt_time, datetime]:
    local_tz = ZoneInfo(config.timezone_name)

    day_name = config.weekly_restart_day.strip().lower()
    if day_name not in WEEKDAYS:
        raise ValueError(
            "WEEKLY_RESTART_DAY must be a weekday name; "
            f"got {config.weekly_restart_day!r}"
        )

    try:
        hour_text, minute_text = config.weekly_restart_time.split(":", 1)
        schedule_time = dt_time(
            hour=int(hour_text),
            minute=int(minute_text),
        )
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "WEEKLY_RESTART_TIME must be HH:MM; "
            f"got {config.weekly_restart_time!r}"
        ) from exc

    try:
        policy_start = datetime.fromisoformat(
            config.weekly_restart_policy_start
        )
    except ValueError as exc:
        raise ValueError(
            "WEEKLY_RESTART_POLICY_START must be ISO-8601 local time; "
            f"got {config.weekly_restart_policy_start!r}"
        ) from exc

    if policy_start.tzinfo is None:
        policy_start = policy_start.replace(tzinfo=local_tz)
    else:
        policy_start = policy_start.astimezone(local_tz)

    return local_tz, WEEKDAYS[day_name], schedule_time, policy_start


def _weekly_occurrence_on_or_before(
    reference: datetime,
    *,
    weekday: int,
    at: dt_time,
    local_tz: ZoneInfo,
) -> datetime:
    local_reference = reference.astimezone(local_tz)
    days_back = (local_reference.weekday() - weekday) % 7
    target_date = (local_reference - timedelta(days=days_back)).date()
    candidate = datetime.combine(target_date, at, tzinfo=local_tz)

    if candidate > local_reference:
        target_date -= timedelta(days=7)
        candidate = datetime.combine(target_date, at, tzinfo=local_tz)

    return candidate


def _weekly_occurrence_after(
    occurrence: datetime,
    *,
    at: dt_time,
    local_tz: ZoneInfo,
) -> datetime:
    next_date = occurrence.astimezone(local_tz).date() + timedelta(days=7)
    return datetime.combine(next_date, at, tzinfo=local_tz)


def evaluate_reboot_requirement(
    record: FleetDevice,
    *,
    config: Config,
    now: datetime,
) -> RebootRequirement:
    local_tz, weekday, schedule_time, policy_start = _restart_schedule(config)
    local_now = now.astimezone(local_tz)

    first_due = _weekly_occurrence_on_or_before(
        policy_start,
        weekday=weekday,
        at=schedule_time,
        local_tz=local_tz,
    )
    if first_due < policy_start:
        first_due = _weekly_occurrence_after(
            first_due,
            at=schedule_time,
            local_tz=local_tz,
        )

    if local_now < first_due:
        return RebootRequirement(
            state="not-active",
            due_at=first_due.astimezone(timezone.utc),
            priority=1,
        )

    applicable = _weekly_occurrence_on_or_before(
        local_now,
        weekday=weekday,
        at=schedule_time,
        local_tz=local_tz,
    )
    if applicable < first_due:
        return RebootRequirement(
            state="not-active",
            due_at=first_due.astimezone(timezone.utc),
            priority=1,
        )

    if record.ring_count != 1 or record.telemetry_status != "fresh":
        return RebootRequirement(
            state="unknown",
            due_at=applicable.astimezone(timezone.utc),
            priority=2,
        )

    if record.last_restart is None:
        return RebootRequirement(
            state="unknown",
            due_at=applicable.astimezone(timezone.utc),
            priority=2,
        )

    if record.last_restart >= applicable.astimezone(timezone.utc):
        next_due = _weekly_occurrence_after(
            applicable,
            at=schedule_time,
            local_tz=local_tz,
        )
        return RebootRequirement(
            state="current",
            due_at=next_due.astimezone(timezone.utc),
            priority=0,
        )

    return RebootRequirement(
        state="missed",
        due_at=applicable.astimezone(timezone.utc),
        priority=3,
    )


def _request_json(
    request: urllib.request.Request,
    *,
    timeout: float,
    retries: int,
) -> dict[str, Any]:
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                payload = response.read().decode("utf-8")
                return json.loads(payload) if payload else {}
        except urllib.error.HTTPError as exc:
            retryable = exc.code == 429 or 500 <= exc.code <= 599
            if not retryable or attempt >= retries:
                body = exc.read().decode("utf-8", errors="replace")
                raise RuntimeError(
                    f"HTTP {exc.code} calling {request.full_url}: {body}"
                ) from exc
            retry_after = exc.headers.get("Retry-After")
            try:
                delay = float(retry_after) if retry_after else 2**attempt
            except ValueError:
                delay = 2**attempt
            delay = min(max(delay, 1.0), 30.0)
            LOG.warning("Graph returned HTTP %s; retrying in %.1fs", exc.code, delay)
            time.sleep(delay)
        except urllib.error.URLError as exc:
            if attempt >= retries:
                raise RuntimeError(
                    f"Network error calling {request.full_url}: {exc}"
                ) from exc
            delay = min(2**attempt, 15)
            LOG.warning("Network error; retrying in %ss: %s", delay, exc)
            time.sleep(delay)
    raise RuntimeError("HTTP retry loop terminated unexpectedly")


def get_access_token(config: Config) -> str:
    token_url = (
        f"https://login.microsoftonline.com/{urllib.parse.quote(config.tenant_id)}/"
        "oauth2/v2.0/token"
    )
    form = urllib.parse.urlencode(
        {
            "client_id": config.client_id,
            "client_secret": config.client_secret,
            "grant_type": "client_credentials",
            "scope": TOKEN_SCOPE,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        token_url,
        data=form,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    payload = _request_json(
        request, timeout=config.http_timeout, retries=config.http_retries
    )
    token = payload.get("access_token")
    if not token:
        raise RuntimeError("Microsoft identity platform did not return an access token")
    return str(token)


def graph_get(config: Config, token: str, url: str) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        method="GET",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        },
    )
    return _request_json(
        request, timeout=config.http_timeout, retries=config.http_retries
    )


def graph_get_all(config: Config, token: str, url: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    while url:
        page = graph_get(config, token, url)
        items.extend(page.get("value", []))
        url = str(page.get("@odata.nextLink") or "")
    return items


def fetch_run_states(config: Config, token: str) -> list[dict[str, Any]]:
    script_id = urllib.parse.quote(config.telemetry_script_id, safe="")
    url = (
        f"{GRAPH_BETA_ROOT}/deviceManagement/deviceHealthScripts/{script_id}/"
        "deviceRunStates?$top=999&$expand=managedDevice"
    )
    return graph_get_all(config, token, url)


def fetch_managed_windows_devices(
    config: Config, token: str
) -> list[dict[str, Any]]:
    url = (
        f"{GRAPH_V1_ROOT}/deviceManagement/managedDevices"
        "?$top=999&$select=deviceName,userPrincipalName,operatingSystem,lastSyncDateTime"
    )
    return graph_get_all(config, token, url)


def fetch_update_rings(config: Config, token: str) -> list[UpdateRing]:
    url = f"{GRAPH_V1_ROOT}/deviceManagement/deviceConfigurations?$top=999"
    configs = graph_get_all(config, token, url)
    rings = [
        UpdateRing(
            ring_id=str(item.get("id") or "").strip(),
            display_name=str(item.get("displayName") or "").strip(),
        )
        for item in configs
        if str(item.get("@odata.type") or "").casefold()
        == "#microsoft.graph.windowsupdateforbusinessconfiguration"
        and str(item.get("id") or "").strip()
        and str(item.get("displayName") or "").strip()
    ]
    if not rings:
        raise RuntimeError(
            "Microsoft Graph returned zero Windows Update Rings; "
            "Reboot Watch will not publish a misleading fleet."
        )
    return rings


def fetch_ring_device_statuses(
    config: Config,
    token: str,
    rings: Iterable[UpdateRing],
) -> list[dict[str, Any]]:
    statuses: list[dict[str, Any]] = []
    for ring in rings:
        ring_id = urllib.parse.quote(ring.ring_id, safe="")
        url = (
            f"{GRAPH_V1_ROOT}/deviceManagement/deviceConfigurations/{ring_id}/"
            "deviceStatuses?$top=999"
        )
        for item in graph_get_all(config, token, url):
            item = dict(item)
            item["_ring_id"] = ring.ring_id
            item["_ring_name"] = ring.display_name
            statuses.append(item)
    return statuses


def parse_managed_windows_devices(
    devices: Iterable[dict[str, Any]],
) -> list[ManagedWindowsDevice]:
    newest_by_device: dict[str, ManagedWindowsDevice] = {}

    for device in devices:
        if str(device.get("operatingSystem") or "").casefold() != "windows":
            continue

        computer_name = str(device.get("deviceName") or "").strip()
        if not computer_name:
            continue

        last_sync_raw = str(device.get("lastSyncDateTime") or "").strip()
        last_sync: datetime | None = None
        if last_sync_raw:
            try:
                last_sync = parse_datetime(last_sync_raw)
            except (TypeError, ValueError):
                LOG.warning(
                    "Ignoring malformed Intune last-sync time for %s",
                    computer_name,
                )

        record = ManagedWindowsDevice(
            computer_name=computer_name,
            user=str(device.get("userPrincipalName") or "").strip(),
            last_sync=last_sync,
        )

        key = computer_name.casefold()
        existing = newest_by_device.get(key)
        if existing is None or (
            record.last_sync is not None
            and (
                existing.last_sync is None
                or record.last_sync > existing.last_sync
            )
        ):
            newest_by_device[key] = record

    return list(newest_by_device.values())


def parse_ring_reports(
    statuses: Iterable[dict[str, Any]],
) -> list[RingReport]:
    newest_by_device_ring: dict[tuple[str, str], RingReport] = {}

    for item in statuses:
        computer_name = str(item.get("deviceDisplayName") or "").strip()
        ring_id = str(item.get("_ring_id") or "").strip()
        ring_name = str(item.get("_ring_name") or "").strip()
        if not computer_name or not ring_id or not ring_name:
            continue

        last_reported_raw = str(item.get("lastReportedDateTime") or "").strip()
        last_reported: datetime | None = None
        if last_reported_raw:
            try:
                last_reported = parse_datetime(last_reported_raw)
            except (TypeError, ValueError):
                LOG.warning(
                    "Ignoring malformed update-ring report time for %s / %s",
                    computer_name,
                    ring_name,
                )

        record = RingReport(
            computer_name=computer_name,
            user=str(item.get("userPrincipalName") or "").strip(),
            ring_id=ring_id,
            ring_name=ring_name,
            status=str(item.get("status") or "unknown").strip() or "unknown",
            last_reported=last_reported,
        )

        key = (computer_name.casefold(), ring_id.casefold())
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


def parse_run_states(
    states: Iterable[dict[str, Any]],
    *,
    now: datetime,
    max_age_hours: float,
) -> list[DeviceTelemetry]:
    newest_by_device: dict[str, DeviceTelemetry] = {}

    for state in states:
        output = str(state.get("preRemediationDetectionScriptOutput") or "")
        match = TELEMETRY_RE.search(output)
        if not match:
            continue

        managed = state.get("managedDevice") or {}
        computer_name = str(
            managed.get("deviceName") or match.group("device") or ""
        ).strip()
        if not computer_name:
            continue

        collected_raw = str(state.get("lastStateUpdateDateTime") or "").strip()
        if not collected_raw:
            continue

        try:
            last_restart = parse_datetime(match.group("lastboot"))
            collected = parse_datetime(collected_raw)
        except (TypeError, ValueError):
            LOG.warning("Skipping malformed telemetry for %s", computer_name)
            continue

        uptime_days = max(
            0.0,
            (now - last_restart).total_seconds() / 86400.0,
        )
        age_hours = max(
            0.0,
            (now - collected).total_seconds() / 3600.0,
        )
        record = DeviceTelemetry(
            computer_name=computer_name,
            user=str(managed.get("userPrincipalName") or ""),
            last_restart=last_restart,
            telemetry_collected=collected,
            uptime_days=uptime_days,
            telemetry_age_hours=age_hours,
            fresh=age_hours <= max_age_hours,
        )

        existing = newest_by_device.get(computer_name.casefold())
        if (
            existing is None
            or record.telemetry_collected > existing.telemetry_collected
        ):
            newest_by_device[computer_name.casefold()] = record

    return list(newest_by_device.values())


def merge_fleet_devices(
    managed_devices: Iterable[ManagedWindowsDevice],
    ring_reports: Iterable[RingReport],
    telemetry_records: Iterable[DeviceTelemetry],
) -> list[FleetDevice]:
    telemetry_by_device = {
        record.computer_name.casefold(): record
        for record in telemetry_records
    }
    rings_by_device: dict[str, list[RingReport]] = {}

    for report in ring_reports:
        rings_by_device.setdefault(
            report.computer_name.casefold(),
            [],
        ).append(report)

    fleet: list[FleetDevice] = []

    for managed in managed_devices:
        key = managed.computer_name.casefold()
        reports = rings_by_device.get(key, [])
        reports = sorted(
            reports,
            key=lambda report: report.ring_name.casefold(),
        )
        ring_names = tuple(report.ring_name for report in reports)
        ring_count = len(ring_names)

        if ring_count == 0:
            ring_state = "none"
            ring_status = "not-reported"
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
                (
                    report.last_reported
                    for report in reports
                    if report.last_reported is not None
                ),
                default=None,
            )
            ring_user = next(
                (report.user for report in reports if report.user),
                "",
            )

        telemetry = telemetry_by_device.get(key)
        if telemetry is None:
            fleet.append(
                FleetDevice(
                    computer_name=managed.computer_name,
                    user=managed.user or ring_user,
                    ring_names=ring_names,
                    ring_count=ring_count,
                    ring_state=ring_state,
                    ring_status=ring_status,
                    ring_last_reported=ring_last_reported,
                    last_restart=None,
                    telemetry_collected=None,
                    uptime_days=None,
                    telemetry_age_hours=None,
                    telemetry_status="missing",
                )
            )
            continue

        fleet.append(
            FleetDevice(
                computer_name=managed.computer_name,
                user=telemetry.user or managed.user or ring_user,
                ring_names=ring_names,
                ring_count=ring_count,
                ring_state=ring_state,
                ring_status=ring_status,
                ring_last_reported=ring_last_reported,
                last_restart=telemetry.last_restart,
                telemetry_collected=telemetry.telemetry_collected,
                uptime_days=telemetry.uptime_days,
                telemetry_age_hours=telemetry.telemetry_age_hours,
                telemetry_status="fresh" if telemetry.fresh else "stale",
            )
        )

    return fleet


def build_top_table(
    records: Iterable[FleetDevice],
    *,
    top_n: int,
    local_tz: ZoneInfo,
) -> str:
    fresh = sorted(
        (
            record
            for record in records
            if record.fresh and record.uptime_days is not None
        ),
        key=lambda record: record.uptime_days or 0.0,
        reverse=True,
    )[:top_n]

    if not fresh:
        return "No fresh Intune reboot telemetry is currently available."

    lines = [
        "#  COMPUTER                 UPTIME   LAST RESTART          USER",
        "-- ------------------------ -------- --------------------- ------------------------------",
    ]
    for index, record in enumerate(fresh, start=1):
        restart = record.last_restart.astimezone(local_tz).strftime(
            "%d/%m/%Y %I:%M %p"
        )
        user = record.user or "-"
        lines.append(
            f"{index:>2} {record.computer_name[:24]:<24} "
            f"{record.uptime_days:>6.1f}d  {restart:<21} {user[:30]}"
        )
    return "\n".join(lines)


def build_metrics(
    records: list[FleetDevice],
    *,
    config: Config,
    now: datetime,
) -> dict[str, str]:
    local_tz = ZoneInfo(config.timezone_name)

    telemetry_reporting = [
        record
        for record in records
        if record.telemetry_status != "missing"
    ]
    fresh = [
        record
        for record in records
        if record.telemetry_status == "fresh"
    ]
    stale = [
        record
        for record in records
        if record.telemetry_status == "stale"
    ]
    missing = [
        record
        for record in records
        if record.telemetry_status == "missing"
    ]

    ring_reporting = [
        record
        for record in records
        if record.ring_count >= 1
    ]
    one_ring = [
        record
        for record in records
        if record.ring_count == 1
    ]
    no_ring = [
        record
        for record in records
        if record.ring_count == 0
    ]
    multiple_ring = [
        record
        for record in records
        if record.ring_count > 1
    ]

    latest_collection = max(
        (
            record.telemetry_collected
            for record in telemetry_reporting
            if record.telemetry_collected is not None
        ),
        default=None,
    )
    max_uptime = max(
        (
            record.uptime_days
            for record in fresh
            if record.uptime_days is not None
        ),
        default=0.0,
    )

    reboot_by_device = {
        record.computer_name.casefold(): evaluate_reboot_requirement(
            record,
            config=config,
            now=now,
        )
        for record in records
    }
    missed_reboot = [
        record for record in records
        if reboot_by_device[record.computer_name.casefold()].state == "missed"
    ]
    current_reboot = [
        record for record in records
        if reboot_by_device[record.computer_name.casefold()].state == "current"
    ]
    unknown_reboot = [
        record for record in records
        if reboot_by_device[record.computer_name.casefold()].state == "unknown"
    ]
    not_active_reboot = [
        record for record in records
        if reboot_by_device[record.computer_name.casefold()].state == "not-active"
    ]

    ranked_devices = sorted(
        records,
        key=lambda record: (
            reboot_by_device[record.computer_name.casefold()].priority,
            record.uptime_days
            if record.uptime_days is not None
            else -1.0,
        ),
        reverse=True,
    )
    ranked_fresh = [
        record
        for record in ranked_devices
        if record.telemetry_status == "fresh"
    ]
    serialised_devices = [
        record.as_json(
            local_tz,
            reboot_by_device[record.computer_name.casefold()],
        )
        for record in ranked_devices
    ]

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
        "reboot_missed_devices": len(missed_reboot),
        "reboot_current_devices": len(current_reboot),
        "reboot_unknown_devices": len(unknown_reboot),
        "reboot_not_active_devices": len(not_active_reboot),
        "weekly_restart_day": config.weekly_restart_day,
        "weekly_restart_time": config.weekly_restart_time,
        "weekly_restart_policy_start": config.weekly_restart_policy_start,
        "max_telemetry_age_hours": config.max_telemetry_age_hours,
        "max_uptime_days": round(max_uptime, 3),
        "over_7_days": sum(
            (record.uptime_days or 0.0) >= 7
            for record in fresh
        ),
        "over_14_days": sum(
            (record.uptime_days or 0.0) >= 14
            for record in fresh
        ),
        "over_30_days": sum(
            (record.uptime_days or 0.0) >= 30
            for record in fresh
        ),
        "devices": serialised_devices,
        "top": [
            record.as_json(
                local_tz,
                reboot_by_device[record.computer_name.casefold()],
            )
            for record in ranked_fresh[: config.top_n]
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
        "intune.windows.reboot.missed.count": str(len(missed_reboot)),
        "intune.windows.reboot.current.count": str(len(current_reboot)),
        "intune.windows.reboot.unknown.count": str(len(unknown_reboot)),
        "intune.windows.reboot.notactive.count": str(len(not_active_reboot)),
        "intune.windows.max.uptime.days": f"{max_uptime:.3f}",
        "intune.windows.uptime.over7.count": str(
            sum(
                (record.uptime_days or 0.0) >= 7
                for record in fresh
            )
        ),
        "intune.windows.uptime.over14.count": str(
            sum(
                (record.uptime_days or 0.0) >= 14
                for record in fresh
            )
        ),
        "intune.windows.uptime.over30.count": str(
            sum(
                (record.uptime_days or 0.0) >= 30
                for record in fresh
            )
        ),
        "intune.windows.last.collection.epoch": str(
            int(latest_collection.timestamp())
            if latest_collection
            else 0
        ),
        "intune.windows.top10": build_top_table(
            records,
            top_n=config.top_n,
            local_tz=local_tz,
        ),
        "intune.windows.summary.json": json.dumps(
            summary,
            separators=(",", ":"),
        ),
    }


def send_metrics(config: Config, metrics: dict[str, str]) -> None:
    failures: list[str] = []

    for key, value in metrics.items():
        command = [
            config.zabbix_sender,
            "-z",
            config.zabbix_server,
            "-p",
            str(config.zabbix_port),
            "-s",
            config.zabbix_host,
            "-k",
            key,
            "-o",
            value,
        ]
        completed = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            failures.append(
                f"{key}: {completed.stdout.strip()}"
            )
        else:
            LOG.debug("Sent %s", key)

    if failures:
        raise RuntimeError(
            "zabbix_sender failure(s): " + " | ".join(failures)
        )


def collect(
    config: Config,
) -> tuple[list[FleetDevice], dict[str, str]]:
    now = datetime.now(timezone.utc)
    token = get_access_token(config)

    raw_managed_devices = fetch_managed_windows_devices(
        config,
        token,
    )
    rings = fetch_update_rings(config, token)
    raw_ring_statuses = fetch_ring_device_statuses(
        config,
        token,
        rings,
    )
    raw_states = fetch_run_states(config, token)

    managed_devices = parse_managed_windows_devices(
        raw_managed_devices
    )
    ring_reports = parse_ring_reports(raw_ring_statuses)
    telemetry_records = parse_run_states(
        raw_states,
        now=now,
        max_age_hours=config.max_telemetry_age_hours,
    )

    records = merge_fleet_devices(
        managed_devices,
        ring_reports,
        telemetry_records,
    )
    metrics = build_metrics(
        records,
        config=config,
        now=now,
    )
    return records, metrics


def parse_args(
    argv: list[str] | None = None,
) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read Intune update-ring and reboot telemetry "
            "and publish fleet metrics to Zabbix."
        )
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Read Graph and print generated metrics without "
            "calling zabbix_sender."
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help=(
            "With --dry-run, print summary JSON instead of "
            "the top-10 table."
        ),
    )
    parser.add_argument(
        "--log-level",
        default=os.getenv("LOG_LEVEL", "INFO"),
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)s %(message)s",
    )

    try:
        config = Config.from_env()
        records, metrics = collect(config)
        summary = json.loads(
            metrics["intune.windows.summary.json"]
        )
        LOG.info(
            (
                "Fleet %d Windows devices "
                "(%d one ring, %d no ring, %d multiple rings; "
                "%d telemetry reporting, %d fresh, %d stale, %d missing; "
                "%d missed reboot, %d current, %d unknown, %d not active)"
            ),
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
            if args.json_output:
                print(metrics["intune.windows.summary.json"])
            else:
                print(metrics["intune.windows.top10"])
            return 0

        send_metrics(config, metrics)
        LOG.info("Published %d Zabbix items", len(metrics))
        return 0
    except Exception as exc:
        LOG.error("%s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
