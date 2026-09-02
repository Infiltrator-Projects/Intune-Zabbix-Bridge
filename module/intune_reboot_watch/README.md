# INTUNE — Reboot Watch

**Release:** 0.3.0  
**Platform:** Zabbix 7.0 LTS  
**Type:** Zabbix dashboard widget/module  
**Project:** Intune-Zabbix-Bridge

INTUNE — Reboot Watch is the Zabbix-native frontend for the bridge's Microsoft Intune reboot telemetry.

It displays the ten longest-running currently fresh Windows devices, actual last restart time, current user, telemetry collection time and age, reporting/fresh/stale counts, maximum uptime, 7/14/30-day counts and collector freshness.

## Data source

Automatic discovery expects a Zabbix text item with key:

`intune.windows.summary.json`

The supplied template creates that item on the conventional host `Microsoft Intune - Windows Fleet`. The widget can also be edited to select another compatible text item explicitly.

## Configuration

The native Zabbix editor exposes only persistent choices:

- fleet summary item;
- rows displayed (1–10);
- collector stale threshold (5–1440 minutes).
