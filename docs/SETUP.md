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

Earlier inventory/update-ring deployments used the following permission set:

- `DeviceManagementManagedDevices.Read.All`
- `DeviceManagementConfiguration.Read.All`
- `DeviceManagementScripts.Read.All`

The shipped 0.7.14 runtime reads remediation run states and does not request Windows Update Rings or a full Windows inventory. The configuration-read permission used by the dormant ring path is not a reason to block telemetry-only collection. Permissions and consent for the active script/run-state endpoint must still be in place. The widget does not provision Zabbix objects automatically.

The browser never receives Graph credentials.

For widget-specific installation/upgrade details, see `module/intune_reboot_watch/docs/INSTALLATION.md`.

For explanations of everything shown on the dashboard, use the [screen guide](../module/intune_reboot_watch/docs/SCREEN_GUIDE.md).
