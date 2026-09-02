# Changelog

## 0.5.0 — 2026-09-02

- added a native Linux Mint GTK configuration utility available from the application menu;
- added a PolicyKit-backed privileged helper so credentials can be saved to /etc without terminal editing;
- the GUI now enables the timer, runs the collector immediately, and reports first-run failures;
- normal setup no longer requires terminal commands, file-manager admin paths, or drag-and-drop configuration.

## 0.4.0 — 2026-09-02

- the native widget automatically creates its Zabbix host group, fleet host and ten trapper items on first use;
- manual template import/linking is no longer required for the normal path;
- automatic provisioning uses public Zabbix APIs and respects the current frontend user's permissions.

## 0.3.0 — 2026-09-02

- promoted the Zabbix frontend to a first-class native module with native configuration, tests and full documentation.
