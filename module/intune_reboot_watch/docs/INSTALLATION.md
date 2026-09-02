# Installation, upgrade and removal

## Debian / Ubuntu / Linux Mint

The normal delivery is the Infiltrator APT package `intune-zabbix-bridge`.

It installs the collector CLI, systemd service/timer, persistent configuration, Zabbix template and `INTUNE — Reboot Watch` under:

`/usr/share/zabbix/modules/intune_reboot_watch`

After installing/upgrading, open **Administration → General → Modules → Scan directory**, enable **INTUNE — Reboot Watch**, then refresh the browser.

Import the supplied template from:

`/usr/share/intune-zabbix-bridge/zabbix/template_intune_zabbix_bridge.yaml`

Create/link the conventional host **Microsoft Intune - Windows Fleet**.

## Portable widget-only installer

```bash
./tools/build-installer.sh
```

This creates `dist/intune-zabbix-reboot-watch-<version>.run`. It installs only the Zabbix frontend module.

## Collector configuration

Configure `/etc/intune-zabbix-bridge/bridge.env` with Entra tenant ID, client ID, client secret, telemetry-script ID and Zabbix destination.

## Upgrade

Debian upgrades preserve `bridge.env` as a conffile. Rescan modules and hard-refresh the browser after frontend upgrades.

## Removal

Package removal stops/disables the bridge timer and removes program/module files. Existing Zabbix history remains governed by Zabbix retention.
