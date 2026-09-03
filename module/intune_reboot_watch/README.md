# INTUNE — Reboot Watch

**Release:** 0.7.4  
**Platform:** Zabbix 7.0 LTS

Reboot Watch has one operational job: show the Windows machines covered by Intune update policy and tell us whether they have satisfied the required weekly restart.

It keeps three independent signals visible:

- current Intune managed-Windows inventory;
- Windows Update Ring `deviceStatuses`, including exactly one / none / multiple ring reporting;
- hourly `Windows - Reboot Telemetry` containing the actual Windows `LastBootUpTime`.

The weekly requirement is evaluated from the real boot time against the configured weekly restart boundary. The St Augustine's defaults mirror the deployed catch-up policy: **Sunday 03:00**, first active occurrence **06/09/2026 03:00 Australia/Melbourne**.

Per-device reboot state is:

- **MISSED** — one ring reported, fresh telemetry, and last boot is before the applicable weekly restart;
- **Current** — last boot is at or after the applicable weekly restart;
- **Unknown** — the policy is active but ring state or reboot telemetry is not trustworthy enough to decide;
- **Not active** — the first configured weekly restart has not happened yet.

Missing ring or telemetry data never makes a computer disappear.

Search covers computer name, username and update-ring name. The default table ordering puts missed/unknown restart states ahead of current machines.

Collector deployment remains one Debian package plus one `intune-zabbix-bridge.env` file.
