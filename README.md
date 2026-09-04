# Intune-Zabbix-Bridge

**Release:** 0.7.9  
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

## Emergency 0.7.9 mode

Windows Update Ring collection is temporarily disabled in the shipped runtime. The existing Entra application does not currently have `DeviceManagementConfiguration.Read.All`; ring enumeration therefore returned HTTP 403 and aborted every 15-minute collector run.

0.7.9 deliberately makes **no update-ring Graph request**. It restores the signals that were already working before ring collection was added:

- current managed-Windows inventory keyed by immutable `managedDevice.id`;
- reboot telemetry joined by expanded `managedDevice.id`;
- telemetry freshness, last restart and uptime;
- normal 15-minute Zabbix publication.

The newer ring-report implementation remains packaged but dormant so it can be re-enabled later after the required Intune permission and report path are deliberately configured and tested. A regression test proves the shipped emergency runtime does not call ring enumeration or ring-report Graph sources.

Because ring collection is disabled, ring and ring-dependent reboot-policy fields are not authoritative in this emergency release. Inventory and reboot telemetry remain authoritative.

The Zabbix widget is read-only. Import/link the packaged `Intune Zabbix Bridge` template and create/link the `Microsoft Intune - Windows Fleet` host during setup; merely opening the dashboard never creates Zabbix objects. Trapper items in the packaged template accept submissions from `127.0.0.1` and `::1` only by default.

The collector refuses to publish an empty Windows estate, sends the summary JSON only after all companion metrics have succeeded, and treats a materially future collector timestamp as unknown rather than current.

Release publication builds and tests the exact DEB and RUN artifacts before creating the private GitHub release. Public APT mirroring is a separate authenticated step and the release workflow fails if that handoff cannot be completed and verified.
