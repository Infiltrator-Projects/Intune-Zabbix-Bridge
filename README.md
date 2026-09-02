# Intune-Zabbix-Bridge

**Release:** 0.5.0  
**Platform:** Microsoft Intune + Zabbix 7.0 LTS  
**Delivery:** Infiltrator APT / Linux Mint Software Manager

Intune-Zabbix-Bridge is a read-only bridge and native Zabbix dashboard module for central Windows reboot telemetry.

The project now has two equally first-class halves:

- a Python collector that reads the existing Intune reboot-telemetry device-health-script results through Microsoft Graph and publishes fleet metrics with `zabbix_sender`;
- a native Zabbix 7.0 frontend widget, **INTUNE — Reboot Watch**, installed under `/usr/share/zabbix/modules/intune_reboot_watch`.

## What the widget shows

- top 10 longest-running fresh Windows devices;
- actual Windows last restart time;
- current user;
- endpoint telemetry collection time and age;
- reporting, fresh and stale device counts;
- maximum fleet uptime;
- 7, 14 and 30 day uptime counts;
- collector-current / collector-stale state.

## Zabbix-native design

The widget has the same engineering model used by WHERE’S WALLY: a manifest, widget class, native edit form, controller, testable helper classes, dedicated view, scoped CSS/JS, package validation, portable installer and operational/security/development/testing documentation.

`module/intune_reboot_watch/manifest.json` is the release-version source of truth. Builders derive package/installer versions from it.

## Installation

The normal installation path is the Infiltrator Software repository in Linux Mint Software Manager. Install or update **Intune Zabbix Bridge**.

Then in Zabbix:

1. **Administration → General → Modules → Scan directory**.
2. Enable **INTUNE — Reboot Watch**.
3. Refresh the browser.
4. Add **INTUNE — Reboot Watch** to the dashboard. The widget self-provisions its Zabbix host and trapper items when needed.

Open **Intune Zabbix Bridge Setup** from the Linux Mint application menu, paste the Entra Tenant ID, Client ID and Client secret, then click **Save & Start Collector**. The utility handles the protected configuration file and systemd timer automatically; no terminal or manual `/etc` editing is required.

## Documentation

- `module/intune_reboot_watch/docs/ARCHITECTURE.md`
- `module/intune_reboot_watch/docs/INSTALLATION.md`
- `module/intune_reboot_watch/docs/OPERATIONS.md`
- `module/intune_reboot_watch/docs/SECURITY.md`
- `module/intune_reboot_watch/docs/DEVELOPMENT.md`
- `module/intune_reboot_watch/docs/TESTING.md`

## Validation

```bash
./tools/test.sh
```

The suite validates PHP, JavaScript, Python, shell, helper contracts, source contracts, Debian packaging and the portable module installer.
