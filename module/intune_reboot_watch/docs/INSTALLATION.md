# Installation, upgrade and removal

## Debian / Ubuntu / Linux Mint

The normal delivery is the Infiltrator APT package `intune-zabbix-bridge`.

It installs the collector CLI, systemd service/timer, persistent configuration, Zabbix template and `INTUNE — Reboot Watch` under:

`/usr/share/zabbix/modules/intune_reboot_watch`

After installing/upgrading, open **Administration → General → Modules → Scan directory**, enable **INTUNE — Reboot Watch**, then refresh the browser.

## Automatic Zabbix-side provisioning

After the module is enabled, adding the widget with its default automatic source selection creates the required Zabbix objects through the authenticated Zabbix API if they do not already exist:

- host group `Microsoft Intune`;
- host `Microsoft Intune - Windows Fleet`;
- ten trapper items used by the collector.

The package still ships `/usr/share/intune-zabbix-bridge/zabbix/template_intune_zabbix_bridge.yaml` for portability/manual use, but importing it is no longer required for the normal path.

## Collector configuration

Open **Intune Zabbix Bridge Setup** from the Linux Mint application menu. Enter the Entra Tenant ID, Client/Application ID and Client secret, then click **Save & Start Collector**. PolicyKit requests administrator authentication, writes the protected `/etc/intune-zabbix-bridge/bridge.env`, enables the timer and runs the collector immediately. No terminal or manual system-file editing is required.

## Portable widget-only installer

```bash
./tools/build-installer.sh
```

This installs only the Zabbix frontend module.

## Upgrade

Debian upgrades preserve `bridge.env` as a conffile. Rescan modules and hard-refresh the browser after frontend upgrades.

## Removal

Package removal stops/disables the bridge timer and removes program/module files. Existing Zabbix objects/history remain governed by Zabbix.
