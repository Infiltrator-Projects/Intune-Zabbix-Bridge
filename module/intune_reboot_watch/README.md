# INTUNE — Reboot Watch

**Release:** 0.6.0  
**Platform:** Zabbix 7.0 LTS

The widget self-provisions its Zabbix host group, fleet host and trapper items.

Collector deployment is one universal Debian package plus one separate `intune-zabbix-bridge.env` file. Put that file in the Linux user's Downloads folder; the package imports it and runs the collector automatically.
