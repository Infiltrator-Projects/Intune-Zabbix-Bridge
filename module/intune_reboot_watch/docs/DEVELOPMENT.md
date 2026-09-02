# Development guide

## Principles

- one operational responsibility per component;
- strict PHP typing;
- deterministic fallback order;
- bounded requests and displayed rows;
- no direct Zabbix database access;
- no Microsoft Graph access from browser code;
- stale data is labelled/excluded, never silently current.

## Release metadata

`module/intune_reboot_watch/manifest.json` is the single source of truth for delivered release version. Debian and portable builders derive from it; tests catch documentation drift.

## PHP boundary

Only `actions/WidgetView.php` may depend on Zabbix API/runtime classes. Parsing/freshness policy belongs in `includes/`.

## JavaScript boundary

The client extends Zabbix `CWidget` but owns no network transport or timer. This preserves a single refresh owner.

## CSS

Selectors use the `irw-` namespace. Presentation is optimised for operational scanning.

## Versioning

Patch = compatible correction. Minor = compatible feature/contract extension. Major = incompatible configuration/data contract.
