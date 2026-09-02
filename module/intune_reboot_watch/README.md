# INTUNE — Reboot Watch

**Release:** 0.7.0  
**Platform:** Zabbix 7.0 LTS

The widget self-provisions its Zabbix host group, fleet host and trapper items.

The fleet table searches all fresh devices by computer name or username. Every column heading is clickable, with a second click reversing the selected sort.

Collector deployment is one universal Debian package plus one separate `intune-zabbix-bridge.env` file. Put that file in the Linux user's Downloads folder; the package imports it and runs the collector automatically.
