# Operations guide

## Normal operation

The collector runs every 15 minutes. The widget uses normal Zabbix refresh scheduling and reads the newest fleet-summary history record.

**Collector current** means summary generation is within the widget threshold. **Collector stale** means it is older. **Collector time unavailable/invalid** means freshness cannot be established.

The fleet row population is the current Intune managed-Windows estate. Ring reporting and reboot telemetry are independent attributes on those rows.

## Table semantics

**Computer** is the current Intune managed-device name.

**Update ring** is the ring name reported through the Windows Update Ring `deviceStatuses` relationship. **Ring state** is One ring, No ring reported, or Multiple rings. For exactly one ring the raw Intune configuration status is displayed beside the state. **Ring reported** is that ring's last report time.

**Telemetry** is Fresh, Stale or Missing for the reboot-telemetry remediation. **Uptime** comes from Windows `LastBootUpTime` when reboot telemetry exists. **Last restart** is the actual Windows boot time. **Telemetry collected** is when that endpoint record was captured. **Age** is reboot-telemetry age at collector generation.

Search matches computer names, usernames and update-ring names without case sensitivity. Click any column heading to sort; click the active heading again to reverse direction. Uptime descending remains the initial view.

## Fault isolation

If the collector fails with an update-ring Graph error, verify `DeviceManagementConfiguration.Read.All` application permission and admin consent. Do not treat an inventory-only result as acceptable.

If **No ring reported** is non-zero, those Windows devices exist in Intune but no current update-ring device status was returned for them.

If **Multiple rings** is non-zero, more than one update-ring device status was returned for those computers and they should be investigated rather than silently choosing one.

If **Missing telemetry** is non-zero, those computers can still have a valid update-ring status; the reboot-telemetry remediation simply has not supplied a usable record.

If the summary item is missing, confirm `intune.windows.summary.json` exists in Latest data.

If it has no history, verify collector configuration/service.

If the collector is stale, check the systemd timer/service and Graph authentication.

If the widget type is absent, scan/enable the module and refresh the browser.
