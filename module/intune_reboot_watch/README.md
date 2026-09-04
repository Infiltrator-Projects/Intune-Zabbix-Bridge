# INTUNE — Reboot Watch

**Release:** 0.7.8  
**Platform:** Zabbix 7.0 LTS

Reboot Watch has one operational job: show the Windows machines covered by Intune update policy and tell us whether they have satisfied the required weekly restart.

It keeps three independent signals visible:

- current Intune managed-Windows inventory, keyed by immutable `managedDevice.id`;
- Windows Update Ring device policy state from Intune's current `getConfigurationPolicyDevicesReport` report;
- `Windows - Reboot Telemetry`, joined to the fleet by expanded `managedDevice.id` and containing the actual Windows `LastBootUpTime`.

Ring report rows are correlated primarily by the report's `IntuneDeviceId`, which maps directly to immutable `managedDevice.id`. Name/UPN matching is only a conservative fallback when it uniquely identifies one current device. Duplicate computer names therefore remain separate and are never silently merged. Duplicate report rows for the same device/ring collapse to the newest report time.

The shipped collector does not use deprecated Windows Update Ring `deviceStatuses` and no longer infers ring membership from `getTargetedUsersAndDevices`. If Intune returns update rings but no usable ring report rows, collection fails instead of publishing a false all-no-ring fleet. The collector runs every 15 minutes, so a substantially older collector age means the dashboard is showing the last successful generation while newer collector attempts are failing.

The weekly requirement is evaluated from the real boot time against the configured weekly restart boundary. The St Augustine's defaults mirror the deployed catch-up policy: **Sunday 03:00**, first active occurrence **06/09/2026 03:00 Australia/Melbourne**.

Per-device reboot state is:

- **MISSED** — exactly one ring reports for the device, telemetry is fresh, and last boot is before the applicable weekly restart;
- **Current** — exactly one ring reports for the device and last boot is at or after the applicable weekly restart;
- **Unknown** — the policy is active but ring state or reboot telemetry is not trustworthy enough to decide;
- **Not active** — the first configured weekly restart has not happened yet.

Missing ring or telemetry data never makes a computer disappear. Operational fault rows are always kept visible even when the normal row limit is exceeded or a search would otherwise hide them. Headline counters are recalculated from those same device rows, so the cards cannot contradict the table.

The widget is read-only and never provisions hosts, groups or items while rendering. Import/link the packaged Zabbix template during setup. Its trapper items accept local submissions only by default.

Collector deployment is one Debian package plus one root-owned `intune-zabbix-bridge.env` file imported through `/etc/intune-zabbix-bridge/import/`.
