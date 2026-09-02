# Intune-Zabbix-Bridge

**Release:** 0.6.0  
**Platform:** Microsoft Intune + Zabbix 7.0 LTS  
**Distribution:** private/internal only

There is one universal Debian package for every installation. It contains no tenant credentials and no site-specific Intune script ID.

Each deployment needs exactly one separate file named `intune-zabbix-bridge.env` with these four values:

```text
AZURE_TENANT_ID=
AZURE_CLIENT_ID=
AZURE_CLIENT_SECRET=
INTUNE_TELEMETRY_SCRIPT_ID=
```

Put that one file in the logged-in Linux user's **Downloads** folder. A systemd path watcher imports it automatically to `/etc/intune-zabbix-bridge/bridge.env`, removes the Downloads copy, enables the collector timer and immediately performs the first collection.

The Zabbix widget self-provisions its host group, fleet host and trapper items.
