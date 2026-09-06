# Architecture

This document describes the shipped 0.7.14 runtime. The packaged update-ring/inventory implementation is dormant and must not be mistaken for the active collection path.

## Active data flow

1. `/usr/bin/intune-zabbix-bridge` calls `intune_zabbix_bridge.current.main`.
2. The collector obtains a Graph token and reads the configured device health script's run states, including expanded managed-device information.
3. `hardened.parse_run_states` extracts valid boot/report timestamps and keeps the newest usable record per immutable `managedDevice.id`. Report age and uptime are calculated at collection time.
4. `current.collect_telemetry_only` builds the represented population from those telemetry records. No full Windows inventory or update-ring request is made.
5. `current.evaluate_reboot_telemetry_only` reuses the weekly schedule evaluator with a synthetic one-ring count. This removes ring membership as a prerequisite while keeping the recorded-boot and freshness rules.
6. Metrics are built and redundant/dormant summary fields are removed. Internal metrics and dry-run JSON stay readable.
7. `hardened.send_metrics` preflights the summary through `transport.encode_summary`, sends the baseline companion items, then sends the summary last.
8. `WidgetView` reads the most recent accessible Zabbix summary history value. `FleetSummary` decodes and normalises it, derives full-population counters, and supplies the complete device list.
9. The PHP view formats the cards/table/footer. JavaScript searches and sorts all supplied rows before applying the visible-row limit.

## Population and identity

The population is usable remediation telemetry, not the tenant's entire enrolled Windows estate. Invalid records and devices without usable reports are omitted. Stale but valid reports remain eligible for rows. Duplicate computer names remain separate when their immutable Intune IDs differ. The compact wire summary omits IDs which the widget does not display; it does not collapse those rows.

## Interpretation boundaries

The [screen guide](SCREEN_GUIDE.md) defines the nine cards, ten columns, status rules and controls. In particular:

- collector freshness and individual telemetry freshness are separate;
- Longest uptime uses fresh telemetry only;
- reboot classification is based on the latest recorded boot, not a live query;
- the weekly evaluator does not require a fresh report to postdate the due occurrence;
- summary-derived device ages, uptime and reboot classifications remain fixed until the next successful collection;
- search and sort do not alter the complete-summary counters.

## Publication and failure handling

Large summaries use a bounded, versioned zlib/base64 envelope within the existing text item. Plain history stays compatible. The encoded budget is 64,000 bytes and decoded budget is 4,000,000 bytes.

Graph errors, zero usable telemetry, encoding errors and failed companion sends prevent a new summary from being published. Earlier companion metrics may already have advanced if a later companion send fails. The widget reads the summary as a single generation.

The widget shows an older readable summary with its age if no new summary arrives. It shows an error panel if the newest stored value itself is invalid; it does not fall back to older history.

## Read-only UI

The widget never creates Zabbix groups, hosts or items, and never restarts devices. Source discovery is read-only. The package supplies the template for explicit setup. The browser's search/sort code operates on supplied rows; Zabbix owns widget refresh requests. Graph credentials remain in the collector environment.
