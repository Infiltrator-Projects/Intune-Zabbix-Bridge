#!/usr/bin/env python3
"""Shipped collector entry point.

The operational runtime intentionally uses the same telemetry population model
that worked before update-ring/inventory expansion: current Intune remediation
run states define the dashboard rows. Update-ring Graph calls stay disabled.

Only the long-standing Zabbix companion keys are sent. Newer reboot/ring counts
remain inside the summary JSON, where the widget derives its cards, so an older
already-linked Zabbix template cannot block the whole generation.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

from . import hardened
from . import collector as legacy

_BASE_REBOOT_EVALUATOR = legacy.evaluate_reboot_requirement

_BASELINE_ZABBIX_KEYS = frozenset({
    "intune.windows.reporting.count",
    "intune.windows.fresh.count",
    "intune.windows.stale.count",
    "intune.windows.max.uptime.days",
    "intune.windows.uptime.over7.count",
    "intune.windows.uptime.over14.count",
    "intune.windows.uptime.over30.count",
    "intune.windows.last.collection.epoch",
    "intune.windows.top10",
    hardened.SUMMARY_KEY,
})


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


def baseline_zabbix_metrics(metrics: dict[str, str]) -> dict[str, str]:
    """Keep publication compatible with the original deployed Zabbix template.

    The dashboard reads reboot/ring counters from summary JSON. Sending those
    counters as separate trapper items is unnecessary and, on deployments whose
    template predates those optional items, causes zabbix_sender to reject the
    generation before the summary commit marker can be sent.
    """
    missing = _BASELINE_ZABBIX_KEYS.difference(metrics)
    if missing:
        raise RuntimeError(
            "Generated metrics are missing required baseline Zabbix keys: "
            + ", ".join(sorted(missing))
        )
    return {
        key: value
        for key, value in metrics.items()
        if key in _BASELINE_ZABBIX_KEYS
    }


def collect_telemetry_only(
    config: legacy.Config,
) -> tuple[list[hardened.FleetDevice], dict[str, str]]:
    """Collect the proven remediation telemetry population without ring calls."""
    now = datetime.now(timezone.utc)
    token = legacy.get_access_token(config)

    raw_states = legacy.fetch_run_states(config, token)
    telemetry_records = hardened.parse_run_states(
        raw_states,
        now=now,
        max_age_hours=config.max_telemetry_age_hours,
    )
    if not telemetry_records:
        raise RuntimeError(
            "Intune returned zero usable reboot telemetry records; "
            "refusing to replace the last known-good dashboard generation."
        )

    # Recreate the pre-inventory-expansion population: devices with actual
    # remediation telemetry are the dashboard population. Immutable Intune IDs
    # are still retained so duplicate computer names remain distinct.
    managed_devices = [
        hardened.ManagedDevice(
            managed_device_id=record.managed_device_id,
            computer_name=record.computer_name,
            user=record.user,
        )
        for record in telemetry_records
    ]

    hardened.LOG.warning(
        "Windows Update Ring collection is temporarily disabled; publishing the current "
        "reboot-telemetry population only."
    )
    records = hardened.merge_fleet_devices(
        managed_devices,
        [],
        telemetry_records,
    )
    metrics = hardened.build_metrics(records, config=config, now=now)
    return records, baseline_zabbix_metrics(metrics)


def main(argv: list[str] | None = None) -> int:
    hardened.collect = collect_telemetry_only  # type: ignore[assignment]
    legacy.evaluate_reboot_requirement = evaluate_reboot_telemetry_only
    return hardened.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
