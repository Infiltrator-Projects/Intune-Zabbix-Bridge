# INTUNE — Reboot Watch

**Release:** 0.7.14


0.7.14 restores collection for summaries above 64,000 bytes using a versioned zlib/base64 envelope. The widget decodes every device row and counter, accepts old plain JSON history, and bounds decoding to 4,000,000 bytes. Upgrade the Debian package to update the collector and widget together; PHP zlib is required for compressed summaries.
**Platform:** Zabbix 7.0 LTS

Reboot Watch is temporarily running in **reboot telemetry only** mode.

The shipped collector makes no Windows Update Ring Graph requests. Ring collection is disabled until its permission and report path are deliberately reintroduced and tested.

0.7.11 restored the proven operational population used by the working collector: devices with actual Intune remediation reboot telemetry. It no longer expands the dashboard to every managed Windows inventory record and marks hundreds of unrelated devices as missing.

0.7.12 fixed the valid-collector/invalid-dashboard failure caused by Zabbix text-history truncation. The collector strips dormant ring/identity fields and the redundant top-ten copy from the wire summary while preserving every displayed device row and counter, with a safe text budget. Version 0.7.14 extends that transport with lossless compression for larger fleets.

0.7.13 fixes two dashboard semantics exposed by the restored full fleet. Column sorting now ranks the complete fleet before the configured display limit is applied, so sorting Last restart, Telemetry collected, Uptime or any other column is genuinely global rather than being distorted by fault rows pinned into the visible set. Uptime colour is now determined only by the displayed uptime value; stale telemetry remains independently orange in the Telemetry column and no longer downgrades a 30+ day uptime from red to amber.

The dashboard shows:

- current Intune reboot-telemetry devices, internally keyed by immutable `managedDevice.id`;
- weekly reboot compliance;
- actual Windows `LastBootUpTime` and uptime;
- telemetry freshness/age and collector freshness.

Weekly reboot compliance is evaluated from fresh reboot telemetry while ring collection is disabled, so an absent ring report does not force every device to Unknown.

For backward compatibility with already-deployed Zabbix templates, the collector sends only the original long-standing companion trapper keys plus the summary JSON. Reboot/ring counters needed by the widget remain inside that summary JSON instead of being allowed to block the generation as optional separate trapper items.

The ring-report implementation remains dormant in the package for later work, but the shipped service does not call it and the widget does not display ring cards, ring columns, ring search terms or ring fault states.

The widget is read-only and never provisions hosts, groups or items while rendering. Import/link the packaged Zabbix template during setup. Its trapper items accept local submissions only by default.

Collector deployment is one Debian package plus one root-owned `intune-zabbix-bridge.env` file imported through `/etc/intune-zabbix-bridge/import/`.
