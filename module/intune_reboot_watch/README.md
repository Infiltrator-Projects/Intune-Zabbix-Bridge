# INTUNE — Reboot Watch

**Release:** 0.7.10  
**Platform:** Zabbix 7.0 LTS

Reboot Watch is temporarily running in **inventory + reboot telemetry only** mode.

The shipped collector makes no Windows Update Ring Graph requests. Ring collection is disabled until its permission and report path are deliberately reintroduced and tested.

0.7.10 removes ring state from the operational dashboard as well as from the runtime collection path. The dashboard now shows only:

- current Intune managed-Windows inventory, keyed by immutable `managedDevice.id`;
- weekly reboot compliance;
- actual Windows `LastBootUpTime` and uptime;
- telemetry freshness/age and collector freshness.

Weekly reboot compliance is evaluated from fresh reboot telemetry while ring collection is disabled, so an absent ring report no longer forces every device to Unknown.

The ring-report implementation remains dormant in the package for later work, but the shipped service does not call it and the widget does not display ring cards, ring columns, ring search terms or ring fault states.

The widget is read-only and never provisions hosts, groups or items while rendering. Import/link the packaged Zabbix template during setup. Its trapper items accept local submissions only by default.

Collector deployment is one Debian package plus one root-owned `intune-zabbix-bridge.env` file imported through `/etc/intune-zabbix-bridge/import/`.
