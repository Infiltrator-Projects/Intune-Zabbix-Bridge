# Architecture

## Purpose

INTUNE — Reboot Watch is an operational view of Windows Update Ring reporting and actual Windows reboot telemetry. Policy reporting and endpoint telemetry are deliberately independent so the absence of one signal cannot make a computer disappear.

## Data flow

```text
Intune managed Windows inventory
        │
        ├─────────────── authoritative estate ───────────────┐
        │                                                    │
Windows Update Rings                                  Windows client
deviceStatuses                                        Intune Management Extension
        │                                                    │
        │                                             Windows - Reboot Telemetry
        │                                                    │
        └──────────── Microsoft Graph ───────────────────────┘
                              │
                              ▼
                    Intune-Zabbix-Bridge
                              │
                         zabbix_sender
                              ▼
                 Microsoft Intune - Windows Fleet
                              │
                 intune.windows.summary.json
                              ▼
                    INTUNE — Reboot Watch
```

## Responsibilities

The current managed-Windows inventory defines the estate. Every current Windows device remains present even when update-ring status or reboot telemetry is absent.

The collector reads every `windowsUpdateForBusinessConfiguration` and its supported `deviceStatuses` relationship. A device is classified as:

- **one** — exactly one update ring has reported that device;
- **none** — no update-ring device status is currently reported;
- **multiple** — more than one update ring reports the device.

For an exactly-one device, the ring name, raw Intune configuration status and last reported time are retained. This is an observed reporting signal; it is not inferred from the reboot telemetry.

The reboot-telemetry remediation remains a separate signal. Its newest record per device provides actual Windows last-boot time and endpoint telemetry freshness. Missing/stale telemetry never removes a row.

The summary therefore contains the complete Windows estate plus ring and reboot states. The legacy bounded `top` list remains fresh-reboot-telemetry-only.

`FleetSummary.php` parses/normalises summary JSON without Zabbix dependencies. `TelemetryState.php` classifies collector freshness. `WidgetForm.php` persists only source item, row count and stale threshold. `WidgetView.php` is the only frontend component that calls Zabbix APIs. Browser JavaScript filters/sorts only the data already supplied by Zabbix and owns no network transport or competing refresh timer.

## Source-item resolution

1. explicitly configured accessible text item;
2. canonical key `intune.windows.summary.json` on `Microsoft Intune - Windows Fleet`;
3. first accessible exact-key text item.

No direct SQL is used.

## Time semantics

The collector emits timezone-aware ISO-8601 values. The frontend converts display times using the active Zabbix/PHP timezone. Collector freshness compares instants in UTC.

## Failure model

The collector fails closed if it cannot read Windows Update Rings; it does not silently fall back to an inventory-only view.

At fleet level, no-ring, multiple-ring, stale-telemetry and missing-telemetry states are explicit. The widget also distinguishes source-not-found, never-populated, malformed-summary, collector-current, collector-stale and collector-time-unknown states.
