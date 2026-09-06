# Intune-Zabbix-Bridge

**Release:** 0.7.14

**Platform:** Microsoft Intune + Zabbix 7.0 LTS  
**Distribution:** public source; public APT package

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

## Telemetry-only mode

Windows Update Ring collection is temporarily disabled in the shipped runtime. The collector makes **no update-ring Graph request**, so a missing `DeviceManagementConfiguration.Read.All` permission cannot stop the 15-minute collection cycle.

The operational dashboard population is the proven set of devices that have actual Intune remediation reboot telemetry. Devices remain keyed internally by immutable `managedDevice.id`, while the widget shows weekly reboot compliance, actual last restart and uptime, telemetry freshness/age and collector freshness.

0.7.14 fixes collection stopping when the fleet summary outgrows the 64,000-byte safe text budget (the live 0.7.13 failure reached approximately 76,550 bytes). Small summaries remain plain JSON. Larger summaries use a versioned zlib/base64 JSON envelope, and the bundled widget decodes it losslessly before parsing the complete fleet. The final envelope must still fit 64,000 bytes; decoded content is bounded at 4,000,000 bytes. Publication is checked before any companion metric is sent, and the summary remains the final generation marker. No rows, values or counters are discarded to fit the transport.

Upgrade with the Debian package so the collector and widget are updated together. Existing plain JSON history remains readable, and `--dry-run --json` remains ordinary uncompressed JSON. The existing Zabbix host, template, item key and deployment credentials remain in use. PHP zlib support is required by the widget for compressed summaries; the Python collector uses its standard-library zlib module.

Update-ring cards, columns, search terms and ring fault states remain removed from the shipped widget while telemetry-only mode is active. The dormant ring-report implementation remains packaged only for later deliberate re-enablement.

The Zabbix widget is read-only. Import/link the packaged `Intune Zabbix Bridge` template and create/link the `Microsoft Intune - Windows Fleet` host during setup; merely opening the dashboard never creates Zabbix objects. Trapper items in the packaged template accept submissions from `127.0.0.1` and `::1` only by default.

The collector refuses to publish an empty telemetry population, sends the summary JSON only after all companion metrics have succeeded, and treats a materially future collector timestamp as unknown rather than current.

Release publication builds and tests the exact DEB and RUN artifacts before creating the versioned GitHub release. The Debian package is published through the public Infiltrator APT repository; deployment credentials remain private and are never embedded in the package.
