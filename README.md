# Intune-Zabbix-Bridge

**Release:** 0.7.4  
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

Reboot Watch combines the current managed-Windows estate, observed Windows Update Ring device status, and actual reboot telemetry. It then compares each trustworthy `LastBootUpTime` with the applicable weekly restart boundary.

The dashboard therefore distinguishes **MISSED**, **Current**, **Unknown**, and **Not active** weekly restart states. Missing ring/telemetry signals remain visible rather than removing the machine.

The Zabbix widget self-provisions its host group, fleet host and trapper items. Search covers computer name, username and update-ring name, and all displayed columns are sortable.
