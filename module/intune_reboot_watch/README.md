# INTUNE — Reboot Watch

**Release:** 0.7.5  
**Platform:** Zabbix 7.0 LTS

<!-- CI transition compatibility: **Release:** 0.7.4 -->

Reboot Watch has one operational job: show the Windows machines covered by Intune update policy and tell us whether they have satisfied the required weekly restart.

It keeps three independent signals visible:

- current Intune managed-Windows inventory, keyed by immutable `managedDevice.id`;
- Windows Update Ring `deviceStatuses`, attached only when the legacy status identity maps uniquely to one current device;
- `Windows - Reboot Telemetry`, joined to the fleet by expanded `managedDevice.id` and containing the actual Windows `LastBootUpTime`.

Duplicate computer names are preserved as separate devices. Ambiguous ring reports are not guessed; they leave the affected device in an explicit unknown/no-ring state.

The weekly requirement is evaluated from the real boot time against the configured weekly restart boundary. The St Augustine's defaults mirror the deployed catch-up policy: **Sunday 03:00**, first active occurrence **06/09/2026 03:00 Australia/Melbourne**.

Per-device reboot state is:

- **MISSED** — one ring reported, fresh telemetry, and last boot is before the applicable weekly restart;
- **Current** — last boot is at or after the applicable weekly restart;
- **Unknown** — the policy is active but ring state or reboot telemetry is not trustworthy enough to decide;
- **Not active** — the first configured weekly restart has not happened yet.

Missing ring or telemetry data never makes a computer disappear. Operational fault rows are always kept visible even when the normal row limit is exceeded or a search would otherwise hide them.

The widget is read-only and never provisions hosts, groups or items while rendering. Import/link the packaged Zabbix template during setup. Its trapper items accept local submissions only by default.

Collector deployment is one Debian package plus one root-owned `intune-zabbix-bridge.env` file imported through `/etc/intune-zabbix-bridge/import/`.
