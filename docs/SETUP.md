# Setup

The normal installation path is the Infiltrator APT repository via Linux Mint Software Manager.

After installation:

1. scan and enable **INTUNE — Reboot Watch** in **Administration → General → Modules**;
2. import `/usr/share/intune-zabbix-bridge/zabbix/template_intune_zabbix_bridge.yaml`;
3. create/link **Microsoft Intune - Windows Fleet**;
4. configure `/etc/intune-zabbix-bridge/bridge.env` with the Entra application and telemetry-script ID;
5. test the collector with `intune-zabbix-bridge --dry-run --json`;
6. verify that the JSON has sensible `one_ring_devices`, `no_ring_devices`, `multiple_ring_devices` and reboot-telemetry counts;
7. enable `intune-zabbix-bridge.timer` when the dry run is correct.

The Entra application is read-only. It needs Microsoft Graph application permissions sufficient to read the current managed-device inventory, Windows Update Ring configuration/status, and device-health-script results. For current Graph permission naming this means:

- `DeviceManagementManagedDevices.Read.All`
- `DeviceManagementConfiguration.Read.All`
- `DeviceManagementScripts.Read.All`

The collector deliberately fails rather than publishing an inventory-only result if Windows Update Rings cannot be read.

The browser never receives Graph credentials.

For widget-specific installation/upgrade details, see `module/intune_reboot_watch/docs/INSTALLATION.md`.
