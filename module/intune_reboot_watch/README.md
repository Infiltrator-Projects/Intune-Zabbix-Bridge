# INTUNE — Reboot Watch

**Release:** 0.7.9  
**Platform:** Zabbix 7.0 LTS

Reboot Watch is temporarily running in **inventory + reboot telemetry only** mode.

The shipped 0.7.9 collector does not make any Windows Update Ring Graph request. This emergency mode was introduced because the existing Entra application does not currently have `DeviceManagementConfiguration.Read.All`; ring enumeration was therefore returning HTTP 403 and aborting every 15-minute collector run.

0.7.9 restores the operational signals that were already working:

- current Intune managed-Windows inventory, keyed by immutable `managedDevice.id`;
- `Windows - Reboot Telemetry`, joined by expanded `managedDevice.id` and containing the actual Windows `LastBootUpTime`;
- normal 15-minute publication to Zabbix.

The ring-report implementation remains in the package but is dormant. It will be re-enabled only after the required Intune permission and report path are deliberately configured and tested. The shipped runtime has a regression test proving it does not call update-ring enumeration or ring-report Graph endpoints.

Because ring collection is disabled, ring/reboot-policy fields must not be treated as authoritative in this emergency release. Device inventory, telemetry freshness, last restart and uptime remain authoritative.

The widget is read-only and never provisions hosts, groups or items while rendering. Import/link the packaged Zabbix template during setup. Its trapper items accept local submissions only by default.

Collector deployment is one Debian package plus one root-owned `intune-zabbix-bridge.env` file imported through `/etc/intune-zabbix-bridge/import/`.
