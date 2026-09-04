#!/usr/bin/env python3
"""Shipped collector entry point.

Emergency 0.7.9 runtime: keep managed-device inventory and reboot telemetry
publishing while Windows Update Ring collection is temporarily disabled.
Ring-report implementation remains in the package for later re-enablement, but
it is not called by the shipped service and therefore cannot block collection.
"""

from __future__ import annotations

from datetime import datetime, timezone

from . import hardened
from . import collector as legacy


def collect_telemetry_only(
    config: legacy.Config,
) -> tuple[list[hardened.FleetDevice], dict[str, str]]:
    """Collect inventory + reboot telemetry without any update-ring Graph call."""
    now = datetime.now(timezone.utc)
    token = legacy.get_access_token(config)

    managed_devices = hardened.parse_managed_windows_devices(
        hardened.fetch_managed_windows_devices(config, token)
    )
    if not managed_devices:
        raise RuntimeError(
            "Microsoft Graph returned zero managed Windows devices; "
            "refusing to publish an empty fleet."
        )

    raw_states = legacy.fetch_run_states(config, token)
    telemetry_records = hardened.parse_run_states(
        raw_states,
        now=now,
        max_age_hours=config.max_telemetry_age_hours,
    )

    hardened.LOG.warning(
        "Windows Update Ring collection is temporarily disabled; "
        "publishing managed-device inventory and reboot telemetry only."
    )
    records = hardened.merge_fleet_devices(
        managed_devices,
        [],
        telemetry_records,
    )
    return records, hardened.build_metrics(records, config=config, now=now)


def main(argv: list[str] | None = None) -> int:
    hardened.collect = collect_telemetry_only  # type: ignore[assignment]
    return hardened.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
