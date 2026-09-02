# Architecture

## Purpose

INTUNE — Reboot Watch turns reboot telemetry already collected by Microsoft Intune into an operational Zabbix fleet view. It separates endpoint collection, Microsoft Graph access, Zabbix transport and frontend presentation.

## Data flow

```text
Windows client
    │ Intune Management Extension
    ▼
Windows - Reboot Telemetry
    │ deviceHealthScript output
    ▼
Microsoft Graph
    │ application read permissions only
    ▼
Intune-Zabbix-Bridge collector
    │ zabbix_sender
    ▼
Microsoft Intune - Windows Fleet
    │ intune.windows.summary.json
    ▼
Zabbix History API
    ▼
INTUNE — Reboot Watch
```

## Responsibilities

The Python collector authenticates to Graph, reads reboot telemetry, keeps the newest record per device, excludes stale endpoint telemetry from the live ranking and sends fleet items to Zabbix.

`FleetSummary.php` parses/normalises summary JSON without Zabbix dependencies. `TelemetryState.php` classifies collector freshness. `WidgetForm.php` persists only source item, row count and stale threshold. `WidgetView.php` is the only frontend component that calls Zabbix APIs. Browser JavaScript owns no network transport or competing refresh timer.

## Source-item resolution

1. explicitly configured accessible text item;
2. canonical key `intune.windows.summary.json` on `Microsoft Intune - Windows Fleet`;
3. first accessible exact-key text item.

No direct SQL is used.

## Time semantics

The collector emits timezone-aware ISO-8601 values. The frontend converts display times using the active Zabbix/PHP timezone. Collector freshness compares instants in UTC.

## Failure model

The widget distinguishes source-not-found, never-populated, malformed-summary, collector-current, collector-stale and collector-time-unknown states. It never silently treats stale data as current.
