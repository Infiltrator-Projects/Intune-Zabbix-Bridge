# Setup

The normal installation path is the Infiltrator APT repository via Linux Mint Software Manager.

After installation:

1. scan and enable **INTUNE — Reboot Watch** in **Administration → General → Modules**;
2. import `/usr/share/intune-zabbix-bridge/zabbix/template_intune_zabbix_bridge.yaml`;
3. create/link **Microsoft Intune - Windows Fleet**;
4. configure `/etc/intune-zabbix-bridge/bridge.env` with the Entra application and telemetry-script ID;
5. confirm the weekly restart schedule. The built-in defaults mirror the current St Augustine's policy:
   `WEEKLY_RESTART_DAY=sunday`,
   `WEEKLY_RESTART_TIME=03:00`,
   `WEEKLY_RESTART_POLICY_START=2026-09-06T03:00:00`,
   `TIMEZONE=Australia/Melbourne`;
6. test through the systemd service so the protected environment file is loaded;
7. enable/keep `intune-zabbix-bridge.timer` when the first collection is correct.

The Entra application is read-only and needs:

- `DeviceManagementManagedDevices.Read.All`
- `DeviceManagementConfiguration.Read.All`
- `DeviceManagementScripts.Read.All`

The collector deliberately fails rather than publishing an inventory-only result if Windows Update Rings cannot be read.

The browser never receives Graph credentials.

For widget-specific installation/upgrade details, see `module/intune_reboot_watch/docs/INSTALLATION.md`.
