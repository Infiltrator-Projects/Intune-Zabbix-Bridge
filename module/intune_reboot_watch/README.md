# INTUNE — Reboot Watch

**Release:** 0.7.3  
**Platform:** Zabbix 7.0 LTS

The widget self-provisions its Zabbix host group, fleet host and trapper items.

Reboot Watch deliberately keeps three independent signals visible:

- the current Intune managed-Windows inventory is the estate;
- Windows Update Ring `deviceStatuses` show which update ring(s) each computer has actually reported to Intune;
- the hourly reboot telemetry script supplies actual Windows `LastBootUpTime`.

A Windows computer never disappears merely because either policy reporting or reboot telemetry is missing. The table explicitly shows **One ring**, **No ring reported**, **Multiple rings**, and **Fresh / Stale / Missing** reboot telemetry.

Search covers computer name, username and update-ring name. Every column heading is sortable.

Collector deployment is one universal Debian package plus one separate `intune-zabbix-bridge.env` file. Put that file in the Linux user's Downloads folder; the package imports it and runs the collector automatically.
