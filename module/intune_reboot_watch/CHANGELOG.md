# Changelog

## 0.4.0 — 2026-09-02

- made the widget self-provision the required Zabbix host group, fleet host and trapper items on first use;
- removed the normal-install requirement to manually import/link the supplied Zabbix template;
- kept provisioning inside Zabbix's authenticated API boundary rather than touching the database directly;
- added a clear ready-but-waiting-for-collector state after automatic bootstrap.

## 0.3.0 — 2026-09-02

- rebuilt the frontend as a first-class Zabbix 7.0 widget;
- added native configuration for source item, row limit and collector-stale threshold;
- added deterministic source discovery and permission-respecting Zabbix API reads;
- split fleet JSON parsing and freshness rules into testable helper classes;
- added explicit error/current/stale operational states;
- added telemetry collection time to the ranking table;
- added full architecture, installation, operations, security, development and testing documentation;
- made manifest.json the release-version source for builders;
- added PHP, JavaScript, Python, shell, source-contract and package regression tests;
- added a portable Zabbix-module installer alongside the Debian package.
