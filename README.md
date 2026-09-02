# Intune-Zabbix-Bridge

A read-only bridge that turns Microsoft Intune device telemetry into useful Zabbix fleet monitoring.

The first integration is **Windows reboot telemetry**: Intune already knows each reporting laptop's actual Windows `LastBootUpTime`; this project reads those results centrally, ranks the longest-running machines, and publishes the fleet summary into Zabbix.

## What it gives Zabbix

- Top 10 Windows machines with the longest current uptime
- Last restart time and signed-in user for each top-10 entry
- Number of devices reporting reboot telemetry
- Fresh versus stale telemetry counts
- Maximum current uptime
- Counts above 7, 14 and 30 days uptime
- Last telemetry collection timestamp
- JSON fleet summary for future dependent items / automation

## Safety

The bridge never contacts, wakes, reboots or remediates laptops. Microsoft Graph access is read-only. A laptop can be at school, at home or on another network; if it has reported into Intune, Zabbix can use the result.

Stale telemetry is deliberately excluded from the top-10 ranking by default. This prevents a device that disappeared months ago from being presented as a currently-running machine.

## Architecture

```text
Windows laptop
    |
    | Intune Management Extension
    v
Windows - Reboot Telemetry
    |
    | Microsoft Graph (read only)
    v
Intune-Zabbix-Bridge
    |
    | zabbix_sender
    v
Microsoft Intune - Windows Fleet
    |
    +-- Top 10 longest uptime
    +-- Reporting / fresh / stale counts
    +-- Maximum uptime
    +-- 7 / 14 / 30 day counts
```

The collector has no third-party Python dependencies; it uses the Python standard library for OAuth client credentials, Graph calls, pagination, retry handling and telemetry parsing. `zabbix_sender` is used for Zabbix delivery.

## Quick start

See [`docs/SETUP.md`](docs/SETUP.md).

Dry-run example after configuration:

```bash
intune-zabbix-bridge --dry-run
```

Example output:

```text
#  COMPUTER                 UPTIME   LAST RESTART          USER
-- ------------------------ -------- --------------------- ------------------------------
 1 S25-28ABC1234             18.7d  14/08/2026 08:22 AM  user@example.edu.au
 2 T25-28DEF5678             14.3d  18/08/2026 03:51 PM  user@example.edu.au
```

## Current Intune source

The deployment currently expects the existing Intune device-health script named `Windows - Reboot Telemetry`, whose output format is:

```text
DEVICE=<computer>;LASTBOOT=<ISO-8601>;UPTIME_HOURS=<hours>
```

The source script ID is configuration, not code, so the bridge can be moved to another tenant or collector without modification.
