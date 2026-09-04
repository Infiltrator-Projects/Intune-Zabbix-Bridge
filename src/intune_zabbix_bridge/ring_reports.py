#!/usr/bin/env python3
"""Current Intune reporting source for Windows Update Ring device state.

Microsoft's current device-configuration reporting framework exposes the
Device and user check-in status list through
/deviceManagement/reports/getConfigurationPolicyDevicesReport.  This module
uses that report instead of the deprecated deviceStatuses feed and instead of
trying to infer effective membership from getTargetedUsersAndDevices.
"""

from __future__ import annotations

import json
import logging
import urllib.request
from datetime import datetime
from typing import Any, Iterable

from . import collector as legacy
from . import hardened

LOG = logging.getLogger("intune-zabbix-bridge")
REPORT_ENDPOINT = (
    f"{legacy.GRAPH_BETA_ROOT}/deviceManagement/reports/"
    "getConfigurationPolicyDevicesReport"
)
POLICY_BASE_TYPE = "Microsoft.Management.Services.Api.DeviceConfiguration"
REPORT_PAGE_SIZE = 50
REPORT_COLUMNS = (
    "IntuneDeviceId",
    "DeviceName",
    "UPN",
    "PolicyStatus",
    "PspdpuLastModifiedTimeUtc",
)


def _post_report(
    config: legacy.Config,
    token: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    request = urllib.request.Request(
        REPORT_ENDPOINT,
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


def _first(page: dict[str, Any], *names: str, default: Any = None) -> Any:
    for name in names:
        if name in page:
            return page[name]
    return default


def normalise_report_rows(page: dict[str, Any]) -> list[dict[str, Any]]:
    """Convert Intune report Schema/Values output into dictionaries.

    The reports API returns rows as positional arrays and separately returns a
    schema describing each column.  Parsing by schema name avoids hard-coding
    column positions and remains correct if Microsoft changes the selected
    column order in its response.
    """
    schema = _first(page, "Schema", "schema", default=[])
    values = _first(page, "Values", "values", default=[])
    if not isinstance(schema, list) or not isinstance(values, list):
        raise RuntimeError("Intune policy report did not return Schema/Values lists.")

    columns: list[str] = []
    for entry in schema:
        if not isinstance(entry, dict):
            columns.append("")
            continue
        columns.append(str(_first(entry, "Column", "column", default="") or "").strip())

    if not columns or not any(columns):
        raise RuntimeError("Intune policy report returned no usable schema columns.")

    rows: list[dict[str, Any]] = []
    for value in values:
        if isinstance(value, dict):
            rows.append(dict(value))
            continue
        if not isinstance(value, list):
            continue
        rows.append({
            column: value[index] if index < len(value) else None
            for index, column in enumerate(columns)
            if column
        })
    return rows


def fetch_ring_targets(
    config: legacy.Config,
    token: str,
    rings: Iterable[legacy.UpdateRing],
) -> list[dict[str, Any]]:
    """Fetch current policy-report rows for every discovered update ring."""
    targets: list[dict[str, Any]] = []

    for ring in rings:
        skip = 0
        ring_rows = 0
        while True:
            escaped_ring_id = ring.ring_id.replace("'", "''")
            payload = {
                "select": list(REPORT_COLUMNS),
                "filter": (
                    f"(PolicyBaseTypeName eq '{POLICY_BASE_TYPE}') and "
                    f"(PolicyId eq '{escaped_ring_id}')"
                ),
                "skip": skip,
                "top": REPORT_PAGE_SIZE,
                "orderBy": ["DeviceName"],
            }
            page = _post_report(config, token, payload)
            rows = normalise_report_rows(page)

            for item in rows:
                target = dict(item)
                target["_ring_id"] = ring.ring_id
                target["_ring_name"] = ring.display_name
                targets.append(target)
            ring_rows += len(rows)

            total_raw = _first(page, "TotalRowCount", "totalRowCount", default=None)
            try:
                total = int(total_raw) if total_raw is not None else None
            except (TypeError, ValueError):
                total = None

            skip += len(rows)
            if not rows:
                break
            if total is not None and skip >= total:
                break
            if len(rows) < REPORT_PAGE_SIZE:
                break

        LOG.info(
            "Windows Update Ring %s policy report returned %d device rows",
            ring.display_name,
            ring_rows,
        )

    return targets


def _unique_identity_maps(
    managed_devices: Iterable[hardened.ManagedDevice],
) -> tuple[dict[str, str], dict[tuple[str, str], str], dict[str, str]]:
    by_id: dict[str, str] = {}
    by_name_user_candidates: dict[tuple[str, str], set[str]] = {}
    by_name_candidates: dict[str, set[str]] = {}

    for device in managed_devices:
        managed_id = device.managed_device_id
        by_id[managed_id.casefold()] = managed_id
        name = device.computer_name.casefold()
        user = device.user.casefold()
        by_name_candidates.setdefault(name, set()).add(managed_id)
        if user:
            by_name_user_candidates.setdefault((name, user), set()).add(managed_id)

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
    return by_id, by_name_user, by_name


def parse_ring_targets(
    managed_devices: list[hardened.ManagedDevice],
    targets: Iterable[dict[str, Any]],
) -> list[hardened.RingReport]:
    """Join current report rows to the managed estate by Intune device ID.

    IntuneDeviceId is the immutable managedDevice.id and is therefore the
    primary join.  Name/UPN is retained only as a conservative compatibility
    fallback when it uniquely resolves to one current managed device.
    """
    by_id, by_name_user, by_name = _unique_identity_maps(managed_devices)
    managed_by_id = {
        device.managed_device_id.casefold(): device for device in managed_devices
    }
    newest_by_device_ring: dict[tuple[str, str], hardened.RingReport] = {}

    for target in targets:
        ring_id = str(target.get("_ring_id") or "").strip()
        ring_name = str(target.get("_ring_name") or "").strip()
        if not ring_id or not ring_name:
            continue

        target_id = str(
            target.get("IntuneDeviceId")
            or target.get("intuneDeviceId")
            or ""
        ).strip()
        target_name = str(
            target.get("DeviceName")
            or target.get("deviceName")
            or ""
        ).strip()
        target_user = str(
            target.get("UPN")
            or target.get("upn")
            or target.get("userPrincipalName")
            or ""
        ).strip()

        managed_device_id = by_id.get(target_id.casefold()) if target_id else None
        if managed_device_id is None and target_name and target_user:
            managed_device_id = by_name_user.get(
                (target_name.casefold(), target_user.casefold())
            )
        if managed_device_id is None and target_name:
            managed_device_id = by_name.get(target_name.casefold())

        if managed_device_id is None:
            LOG.warning(
                "Not attaching unresolved update-ring report %s / %s (IntuneDeviceId=%s)",
                target_name or "<unnamed>",
                ring_name,
                target_id or "<none>",
            )
            continue

        managed = managed_by_id[managed_device_id.casefold()]
        modified_raw = str(
            target.get("PspdpuLastModifiedTimeUtc")
            or target.get("pspdpuLastModifiedTimeUtc")
            or ""
        ).strip()
        last_reported: datetime | None = None
        if modified_raw:
            try:
                last_reported = legacy.parse_datetime(modified_raw)
            except (TypeError, ValueError):
                LOG.warning(
                    "Ignoring malformed policy report time for %s / %s",
                    managed.computer_name,
                    ring_name,
                )

        status_raw = target.get("PolicyStatus")
        if status_raw is None:
            status_raw = target.get("policyStatus")
        status = str(status_raw if status_raw is not None else "unknown").strip()
        if not status:
            status = "unknown"

        record = hardened.RingReport(
            managed_device_id=managed_device_id,
            computer_name=managed.computer_name,
            user=target_user or managed.user,
            ring_id=ring_id,
            ring_name=ring_name,
            status=status,
            last_reported=last_reported,
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
