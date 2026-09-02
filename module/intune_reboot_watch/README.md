# INTUNE — Reboot Watch

**Release:** 0.4.0  
**Platform:** Zabbix 7.0 LTS  
**Type:** Zabbix dashboard widget/module  
**Project:** Intune-Zabbix-Bridge

INTUNE — Reboot Watch is the Zabbix-native frontend for the bridge's Microsoft Intune reboot telemetry.

It displays the ten longest-running currently fresh Windows devices, actual last restart time, current user, telemetry collection time and age, reporting/fresh/stale counts, maximum uptime, 7/14/30-day counts and collector freshness.

## Automatic Zabbix bootstrap

With automatic source selection, the widget now provisions its own Zabbix-side data model on first use through the authenticated Zabbix API:

- host group `Microsoft Intune`;
- host `Microsoft Intune - Windows Fleet`;
- all ten trapper items expected by the collector.

This is idempotent and permission-aware. It does not write directly to the Zabbix database. An administrator no longer needs to import/link the supplied template for the normal installation path.

## Configuration

The native Zabbix editor exposes only persistent choices:

- optional explicit fleet summary item;
- rows displayed (1–10);
- collector stale threshold (5–1440 minutes).
