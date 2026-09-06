# Operations guide

Current behaviour: release 0.7.14, reboot telemetry only.

For every card, column, colour, banner, control and editor field, use the [screen guide](SCREEN_GUIDE.md). Its definitions follow the shipped code, including the reporting-population and weekly-boundary limitations.

## Collection and display

The systemd service is `intune-zabbix-bridge.service`; its timer schedules a run approximately every 15 minutes. The widget's default refresh is 60 seconds, managed by Zabbix. Refreshing the widget reads stored history; it does not trigger Intune reporting or a collector run.

The represented population consists of devices with usable reboot telemetry from the configured Intune remediation script. Records are joined and deduplicated by immutable `managedDevice.id`. Devices with no usable record are omitted; old usable records can remain as stale. `Windows` is therefore not the tenant's enrolled-device count, and `Telemetry missing = 0` does not prove complete tenant coverage.

The runtime makes no Windows Update Ring Graph requests. Ring counts in service logs describe dormant fields and do not gate the shipped reboot classification. The ring-disabled warning alone is not an error.

## Weekly reboot evaluation

The configured defaults are Sunday 03:00, `Australia/Melbourne`, with policy start `2026-09-06T03:00:00`.

- Before the first applicable occurrence: Not active.
- Once active, stale/missing telemetry or unavailable last restart: Unknown.
- Fresh telemetry with last restart at or after the latest applicable occurrence: Current.
- Fresh telemetry with last restart before that occurrence: MISSED.

Freshness defaults to 48 hours (`MAX_TELEMETRY_AGE_HOURS`). The evaluator does not additionally require the report timestamp to be after the weekly occurrence. A recent-enough pre-boundary report can therefore produce MISSED until a newer boot report arrives. The widget does not execute or confirm a restart task.

## Distinguishing old data

Collector age uses the summary's `generated_at` against current time. It is independent of the companion `intune.windows.last.collection.epoch`, which records the newest device-report timestamp in the population. The footer's `Zabbix received` uses the selected summary history entry's clock.

When generation or publication fails, the previous summary can remain visible and become Collector stale. Its device ages, uptime estimates and reboot classifications remain values from that old collection. A current collector can also publish stale individual device reports.

An invalid newest stored value produces an error panel. The widget does not scan back through history to find an older valid value.

## Summary publication and compression

The service publishes the original nine companion metrics followed by `intune.windows.summary.json`, for ten items in total. The summary acts as the generation marker. A companion-send failure prevents the summary from advancing, although earlier companion items may already have been updated.

From 0.7.14, summaries above 64,000 bytes use the `intune-zabbix-zlib-v1` JSON envelope with `uncompressed_bytes` and base64 `data`. The encoded value must fit 64,000 bytes; decoded content is bounded at 4,000,000 bytes. No represented device rows are dropped to fit. Encoding is checked before any companion item is sent.

The widget checks the envelope version, size, base64/zlib data and decoded content. Python uses its standard-library zlib module; the PHP frontend needs `gzuncompress`. Old plain JSON history remains readable, and `--dry-run --json` remains uncompressed JSON.

A compressed publication logs its raw and encoded byte counts. A successful service run ends with `Published 10 Zabbix items`. If even the compressed summary is too large, the error states that explicitly and no metrics are sent for that attempt.

## Deployment

Use the Debian package to upgrade both the collector and widget. The RUN installer updates the widget only. Existing host/template configuration and the protected deployment environment remain in use. See [installation](INSTALLATION.md) for the actual setup path.
