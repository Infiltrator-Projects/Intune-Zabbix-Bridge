# INTUNE — Reboot Watch

**Release:** 0.7.2  
**Platform:** Zabbix 7.0 LTS

The widget self-provisions its Zabbix host group, fleet host and trapper items.

The fleet table uses Intune's managed Windows inventory as the authoritative device list and left-joins reboot telemetry onto it. Devices with stale or missing telemetry remain visible and searchable instead of disappearing. Every column heading is clickable, with a second click reversing the selected sort.

Collector deployment is one universal Debian package plus one separate `intune-zabbix-bridge.env` file. Put that file in the Linux user's Downloads folder; the package imports it and runs the collector automatically.
