# Installation, upgrade and removal

Current package: release 0.7.14. See the [screen guide](SCREEN_GUIDE.md) for normal use and the three Reboot Watch-specific widget settings.

## Debian / Ubuntu / Linux Mint

The `intune-zabbix-bridge` Debian package contains the collector CLI, systemd service/timer, protected configuration-import helper, Zabbix template and frontend module.

The widget is installed under `/usr/share/zabbix/modules/intune_reboot_watch`. Python modules are installed under `/usr/lib/python3/dist-packages/intune_zabbix_bridge`.

## Zabbix setup

1. Scan the module directory in Zabbix's module administration and enable INTUNE - Reboot Watch.
2. Import `/usr/share/intune-zabbix-bridge/zabbix/template_intune_zabbix_bridge.yaml`.
3. Create or select the collector's target host, normally `Microsoft Intune - Windows Fleet`, and link the template.
4. Add the widget to the dashboard. Automatic source selection prefers that host's summary text item; an explicit Fleet summary item selection overrides discovery.

Opening the widget never creates a host group, host or item. Template/host setup is required; the old automatic-provisioning description did not match the shipped code. Trapper items accept local submissions from `127.0.0.1` and `::1` by default.

## Collector configuration

The shipped package uses an environment file, not a graphical setup application. Supply `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET` and `INTUNE_TELEMETRY_SCRIPT_ID` in a deployment file. Import it through the protected inbox described in the [repository README](../../../README.md).

The helper writes `/etc/intune-zabbix-bridge/bridge.env`, removes the inbox copy, enables the timer and starts collection when the configuration is ready. Credentials are not embedded in the package or sent to the browser.

The collector evaluates its configured weekly day/time, policy-start timestamp and timezone. The deployed Intune telemetry assignment determines client reporting frequency. The widget's freshness and display settings do not change either schedule.

## Upgrade

Use the DEB to update the collector and widget together. Existing `bridge.env` is not shipped inside the package and is retained across ordinary upgrades. When it finds configured credentials, the post-install script enables the timer and attempts a collector restart. Check the service log to confirm publication.

The frontend must provide PHP zlib for compressed summaries. Zabbix does not need a database schema or summary-item change for 0.7.14. Refresh the dashboard to load the current widget code and data.

## Portable widget-only installer

`tools/build-installer.sh` builds the RUN installer. It installs only the frontend module, so it cannot by itself upgrade the Python collector or its transport encoder.

## Removal

Package removal stops/disables the bridge timer and import watcher and removes packaged program/module files. Existing Zabbix objects and history remain governed by Zabbix.
