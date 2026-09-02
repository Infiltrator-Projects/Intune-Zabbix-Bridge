# Changelog

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
