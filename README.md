# Intune-Zabbix-Bridge

**Release:** 0.7.7  
**Platform:** Microsoft Intune + Zabbix 7.0 LTS  
**Distribution:** private/internal only

There is one Debian package for deployment. It contains no tenant credentials and no site-specific Intune script ID.

Each deployment needs `intune-zabbix-bridge.env` with:

```text
AZURE_TENANT_ID=
AZURE_CLIENT_ID=
AZURE_CLIENT_SECRET=
INTUNE_TELEMETRY_SCRIPT_ID=
```

Optional weekly restart settings are supported. Current St Augustine's defaults are:

```text
WEEKLY_RESTART_DAY=sunday
WEEKLY_RESTART_TIME=03:00
WEEKLY_RESTART_POLICY_START=2026-09-06T03:00:00
TIMEZONE=Australia/Melbourne
```

Copy the deployment file into the protected root-only import inbox:

```bash
sudo install -o root -g root -m 0600 intune-zabbix-bridge.env \
  /etc/intune-zabbix-bridge/import/intune-zabbix-bridge.env
```

The package imports it into `/etc/intune-zabbix-bridge/bridge.env`, removes the inbox copy, enables the timer and performs the first collection. Per-user Downloads folders are not trusted.

Reboot Watch combines the current managed-Windows estate, effective Windows Update Ring targeting membership, and actual reboot telemetry. Managed-device identity is keyed by immutable Intune `managedDevice.id`; duplicate computer names are not collapsed. Reboot telemetry is joined by that ID.

Ring membership is now read from Intune's `getTargetedUsersAndDevices` targeting action for each Windows Update Ring instead of the deprecated `deviceConfigurationDeviceStatus`/`deviceStatuses` path. Returned device identities are correlated first by immutable managed-device ID, then Azure AD device ID, with name/UPN fallback only when it resolves uniquely. If Intune returns rings but no resolvable targeted Windows devices, the collector fails closed instead of publishing a false all-unassigned fleet.

The dashboard distinguishes **MISSED**, **Current**, **Unknown**, and **Not active** weekly restart states. Missing ring/telemetry signals remain visible rather than removing the machine, and fault rows are not hidden by the normal display limit or search filter. Headline counters are derived from the same authoritative device rows shown in the table, so the cards cannot contradict those rows.

The Zabbix widget is read-only. Import/link the packaged `Intune Zabbix Bridge` template and create/link the `Microsoft Intune - Windows Fleet` host during setup; merely opening the dashboard never creates Zabbix objects. Trapper items in the packaged template accept submissions from `127.0.0.1` and `::1` only by default.

The collector refuses to publish an empty Windows estate, sends the summary JSON only after all companion metrics have succeeded, and treats a materially future collector timestamp as unknown rather than current.

Release publication is end-to-end: the exact tested DEB is mirrored into the central Infiltrator APT repository, and the release job does not succeed until both the public catalogue and APT `Packages.gz` advertise the same version.
