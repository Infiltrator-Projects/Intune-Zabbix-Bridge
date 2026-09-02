# Operations guide

## Normal operation

The collector runs every 15 minutes. The widget uses normal Zabbix refresh scheduling and reads the newest fleet-summary history record.

**Collector current** means summary generation is within the widget threshold. **Collector stale** means it is older. **Collector time unavailable/invalid** means freshness cannot be established.

The ranking includes only endpoint telemetry the collector considers fresh.

## Table semantics

**Computer** is the Intune managed-device name. **Uptime** comes from Windows `LastBootUpTime`. **Last restart** is the actual Windows boot time. **Telemetry collected** is when that endpoint record was captured. **Age** is endpoint telemetry age at collector generation.

Search matches computer names and usernames without case sensitivity. Click any column heading to sort the complete fresh-device list; click the active heading again to reverse direction. Uptime descending remains the initial view, and the configured row count limits only how many matches are visible rather than what can be searched.

## Fault isolation

If the summary item is missing, confirm the template is linked and `intune.windows.summary.json` exists in Latest data.

If it has no history, verify collector configuration/service.

If the collector is stale, check the systemd timer/service and Graph authentication.

If fewer than ten rows appear, inspect Reporting/Fresh/Stale counts; stale endpoint telemetry is deliberately excluded.

If the widget type is absent, scan/enable the module and refresh the browser.
