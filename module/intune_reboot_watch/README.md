# INTUNE — Reboot Watch

**Release:** 0.7.11  
**Platform:** Zabbix 7.0 LTS

Reboot Watch is temporarily running in **reboot telemetry only** mode.

The shipped collector makes no Windows Update Ring Graph requests. Ring collection is disabled until its permission and report path are deliberately reintroduced and tested.

0.7.11 restores the proven operational population used by the working collector: devices with actual Intune remediation reboot telemetry. It no longer expands the dashboard to every managed Windows inventory record and mark hundreds of unrelated devices as missing.

The dashboard shows:

- current Intune reboot-telemetry devices, keyed by immutable `managedDevice.id`;
- weekly reboot compliance;
- actual Windows `LastBootUpTime` and uptime;
- telemetry freshness/age and collector freshness.

Weekly reboot compliance is evaluated from fresh reboot telemetry while ring collection is disabled, so an absent ring report does not force every device to Unknown.

For backward compatibility with already-deployed Zabbix templates, the collector sends only the original long-standing companion trapper keys plus the summary JSON. Reboot/ring counters needed by the widget remain inside that summary JSON instead of being allowed to block the generation as optional separate trapper items.

The ring-report implementation remains dormant in the package for later work, but the shipped service does not call it and the widget does not display ring cards, ring columns, ring search terms or ring fault states.

The widget is read-only and never provisions hosts, groups or items while rendering. Import/link the packaged Zabbix template during setup. Its trapper items accept local submissions only by default.

Collector deployment is one Debian package plus one root-owned `intune-zabbix-bridge.env` file imported through `/etc/intune-zabbix-bridge/import/`.
