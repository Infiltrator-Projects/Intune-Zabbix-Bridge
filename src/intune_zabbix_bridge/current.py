#!/usr/bin/env python3
"""Shipped collector entry point.

Emergency telemetry-only runtime: managed-device inventory and reboot telemetry
continue publishing while Windows Update Ring collection is temporarily disabled.
Ring-report implementation remains packaged for later re-enablement, but the
shipped service does not call it and reboot compliance does not depend on it.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

from . import hardened
from . import collector as legacy

_BASE_REBOOT_EVALUATOR = legacy.evaluate_reboot_requirement


def evaluate_reboot_telemetry_only(
    record: hardened.FleetDevice,
    *,
    config: legacy.Config,
    now: datetime,
) -> legacy.RebootRequirement:
    """Evaluate weekly reboot compliance from fresh reboot telemetry alone.

    The legacy evaluator treats an exact one-ring report as a prerequisite.
    Ring collection is intentionally disabled in this runtime, so present a
    synthetic one-ring count only to that evaluator. No ring data is published
    or displayed, and no ring Graph endpoint is called.
    """
    return _BASE_REBOOT_EVALUATOR(
        replace(record, ring_count=1),
        config=config,
        now=now,
    )


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
    legacy.evaluate_reboot_requirement = evaluate_reboot_telemetry_only
    return hardened.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
