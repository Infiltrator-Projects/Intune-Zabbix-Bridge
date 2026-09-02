# Setup

The normal installation path is the Infiltrator APT repository via Linux Mint Software Manager.

After installation:

1. scan and enable **INTUNE — Reboot Watch** in **Administration → General → Modules**;
2. import `/usr/share/intune-zabbix-bridge/zabbix/template_intune_zabbix_bridge.yaml`;
3. create/link **Microsoft Intune - Windows Fleet**;
4. configure `/etc/intune-zabbix-bridge/bridge.env` with the Entra application and telemetry-script ID;
5. test the collector with `intune-zabbix-bridge --dry-run`;
6. enable `intune-zabbix-bridge.timer` when the dry run is correct.

The Entra application should use read-only Microsoft Graph application permissions sufficient to read managed-device and device-health-script results. The browser never receives these credentials.

For widget-specific installation/upgrade details, see `module/intune_reboot_watch/docs/INSTALLATION.md`.
