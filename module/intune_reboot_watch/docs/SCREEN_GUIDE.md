# INTUNE - Reboot Watch: screen guide

For dashboard users and support staff. Checked against release **0.7.14**, source commit `6ef81d779365ba855c91c02bc452e184e782394e`, on 7 September 2026.

## 1. Reading the overview

Reboot Watch displays Windows reboot telemetry already reported through Intune. It compares recorded Windows boot times with a configured weekly restart schedule. The widget is read-only: its cards, device names and status badges do not restart computers or change Intune settings. The surrounding Zabbix menus and dashboard controls belong to Zabbix.

Read the screen from top to bottom: collector health, fleet totals, search and result count, device table, then the footer. The two stale indicators measure different things: **Collector stale** concerns the fleet summary; **Telemetry stale** concerns an individual device's report.

### The nine summary cards

| Card | What its value means |
| --- | --- |
| Windows | Number of devices in the complete usable reboot-telemetry summary. This can be lower than the number enrolled in Intune. |
| Missed reboot | Devices currently classified MISSED by the schedule comparison. The count turns red when greater than zero. |
| Reboot current | Devices with fresh telemetry whose recorded boot is at or after the latest applicable weekly restart time. Green. |
| Reboot unknown | Devices whose restart requirement is active but whose available telemetry cannot support a current/missed classification. Amber when greater than zero. |
| Not active | Devices evaluated before the first configured weekly restart occurrence. This describes the restart policy's start, not whether a computer is online. |
| Telemetry fresh | Devices whose report age is within the collector's freshness threshold, normally 48 hours. Green. |
| Telemetry stale | Devices with usable but older reports. Amber when greater than zero. |
| Telemetry missing | Rows classified as having no telemetry. Red when greater than zero. The shipped telemetry-only collector normally produces zero here because devices without usable reports are omitted from its population. |
| Longest uptime | Highest uptime among devices with fresh telemetry, shown in days to one decimal place. Cyan is an accent, not a reboot-status judgement. If there are no eligible values, it shows 0.0 d. |

The cards describe the complete summary. Searching, sorting or changing the number of displayed rows does not change their totals. A stale summary leaves its previous counts and row values visible; the collector banner identifies that age.

**Example:** Windows 235, Missed reboot 40, Reboot current 102 and Reboot unknown 93 describe 235 represented devices. Telemetry fresh 142 plus Telemetry stale 93 also totals 235. These are two classifications of the same population, so they must not be added together.

<!-- pagebreak -->

## 2. Every device-table column

| Column | What it shows |
| --- | --- |
| # | Position within the currently visible results, renumbered from 1 after search/sort. It is not a device identifier. Sorting this column restores or reverses the original priority order. |
| Computer | Computer name supplied by Intune, with the name in the telemetry output as a fallback. Distinct Intune device IDs can have the same name and remain separate rows. |
| User | Intune's associated user principal name, usually an email-style username. This is not a live reading of who is currently logged on. |
| Reboot | MISSED, Current, Unknown or Not active. The next section explains the exact rules. |
| Due / next | For MISSED or Unknown: the latest applicable weekly restart time. For Current: the next weekly occurrence. For Not active: the first applicable occurrence. This is a schedule timestamp, not a countdown. |
| Uptime | Days between the collector run and the last recorded Windows boot, rounded to one decimal for display. It is calculated from the boot timestamp, not copied from the script's UPTIME_HOURS value. |
| Last restart | Last Windows boot timestamp contained in the device's latest usable telemetry. It is historical evidence from that report. |
| Telemetry | Fresh, Stale or Missing for this row's report. Fresh normally allows reports up to 48 hours old; it does not mean the computer is online now. |
| Telemetry collected | Intune's lastStateUpdateDateTime for the selected remediation run-state record. This is separate from the time the bridge collected the fleet or Zabbix received it. |
| Age | Hours between the collector run and Telemetry collected, displayed to one decimal place. This age is stored in the summary and changes on a new collection. |

### Colours and missing values

| Indicator | Meaning |
| --- | --- |
| Green uptime | Below 7 days. |
| Amber uptime | At least 7 but below 14 days. |
| Red uptime | At least 14 days; the code distinguishes high (14 to below 30) and critical (30 or more), using the same red colour. |
| Red uptime with a dash | Uptime is unavailable. |
| Reboot badges | MISSED is red; Current green; Unknown amber; Not active muted blue-grey. MISSED also gives the row a light red background. |
| Telemetry badges | Fresh is green; Stale amber; Missing red. Missing telemetry also gives the row a light red background. |

Displayed rounding can make a value near a colour threshold appear to sit on it. Uptime colour and reboot status are independent. A short uptime can still predate the latest weekly restart time. A red uptime can appear alongside stale telemetry. The Longest uptime card can be lower than a stale row's uptime because the card excludes stale rows.

Blank users, absent timestamps and unavailable numeric values display a dash. Row dates use day/month/year and a 12-hour clock with seconds in the PHP frontend's effective timezone. Weekly schedule evaluation uses the collector's configured timezone; these timezone settings can differ.

<!-- pagebreak -->

## 3. Reboot status and the weekly schedule

The collector finds the most recent scheduled weekly restart occurrence at or before the collection time, subject to the policy start. It compares the device's recorded boot against that occurrence. A restart at the exact scheduled timestamp counts as Current.

| Reboot state | Rule used by release 0.7.14 | Due / next |
| --- | --- | --- |
| Not active | The first scheduled occurrence on or after policy start has not arrived. This check happens before telemetry freshness is considered. | First applicable occurrence. |
| Unknown | The policy is active and telemetry is stale/missing, or the last restart is unavailable. Update-ring membership is not a condition in the shipped telemetry-only runtime. | Latest applicable occurrence. |
| Current | The policy is active, telemetry is fresh and last restart is at or after the latest applicable occurrence. | Next weekly occurrence. |
| MISSED | The policy is active, telemetry is fresh and last restart is before the latest applicable occurrence. | Latest applicable occurrence. |

The shipped defaults are **Sunday at 03:00**, timezone **Australia/Melbourne**, with policy start **6 September 2026 at 03:00**. Deployments can override these settings. The footer displays the schedule and policy-start values supplied in the summary. A policy start between weekly occurrences makes the first following occurrence the first due time.

The widget reports this comparison. It does not confirm that an Intune restart task executed, and a Current result does not identify what caused the reboot. Any recorded boot meeting the time comparison qualifies.

### Freshness is a separate test

The collector's default threshold is **48 hours**: report age at or below that threshold is Fresh; older reports are Stale. This setting is separate from the widget's default **30-minute collector-stale threshold**. Freshness does not establish that a device is online.

**Timing limitation in this release:** the reboot evaluator does not require Telemetry collected to be after the weekly due time. A report from before that time can still be Fresh under the 48-hour rule and yield MISSED. The result describes the available recorded boot; it does not exclude a more recent reboot which has not yet been reported.

### Examples with a Sunday 03:00 due time

| Evidence at the next collection | Result |
| --- | --- |
| Fresh report; recorded boot Sunday 04:00 | Current; Due / next moves to the following Sunday. |
| Fresh report; recorded boot Saturday 20:00 | MISSED; Due / next remains the Sunday just passed. |
| Stale report, whatever its recorded boot time | Unknown once the policy is active. |
| Collection before the first policy occurrence | Not active, including rows with stale telemetry. |

These classifications, uptime and device-report age are calculated when a new summary is generated. Merely refreshing the dashboard does not recalculate them.

<!-- pagebreak -->

## 4. Search, sorting, counts and footer

**Search computer or username** matches a case-insensitive substring of either field. A partial name or part of an email address works. Spaces at the ends are ignored; the remaining input is one search string. It does not search dates, reboot states or update-ring names. Clearing the box restores the unfiltered results.

Search and sorting use every row in the received fleet summary before applying the display limit. The default is 10 visible rows, configurable from 1 to 10. There are no page-navigation controls in this widget. A search can reveal a device outside the first ten rows.

| Result count | How to read it |
| --- | --- |
| 10 / 235 | Ten visible rows from 235 represented devices, with no search active. |
| 10 shown · 24 matches · 235 total | Twenty-four devices match the search; the first ten in the selected order are visible. |
| No computers or usernames match the search. | No rows matched the search. The fleet cards retain their complete-summary totals. |

### Clickable column headings

Click a heading to sort; click the active heading again to reverse direction. An upward arrow means ascending and a downward arrow means descending. The double arrow marks an inactive sortable heading. Keyboard focus and activation are supported.

| Heading | Initial direction when selected |
| --- | --- |
| # | Original priority order first; reverse gives its opposite. |
| Computer / User | Alphabetical ascending, with natural numeric comparison. |
| Reboot | MISSED, Unknown, Not active, Current. This is the initial active sort. |
| Due / next | Earliest timestamp first. |
| Uptime | Highest uptime first. |
| Last restart | Most recent timestamp first. |
| Telemetry | Alphabetical status order: Fresh, Missing, Stale. |
| Telemetry collected | Most recent timestamp first. |
| Age | Oldest device report first. |

Ties retain the original fleet rank: reboot priority followed by greatest uptime. Blank text or numeric sort values go last in either direction. Missing/invalid timestamps use zero internally, so they appear before valid dates in ascending date sorts and after them in descending sorts. Sorting uses stored numeric values, not the formatted text shown on screen.

Search text and sort choice survive normal widget refreshes while the widget remains loaded. They are not stored as a permanent saved preference; a full reload can reset them.

**Footer:** Weekly restart gives the configured weekday/time and policy start. “Sort/search use the complete fleet before the display limit.” confirms the table behaviour. Zabbix received is the stored history timestamp of the summary being displayed; it is separate from device report time and summary generation time.

<!-- pagebreak -->

## 5. Collector health and widget settings

The top banner compares current server time with the summary's generated_at timestamp. Its age is shown in minutes to one decimal place and recalculated on widget refresh. It does not directly inspect the service. **A green 13.8 min is normal within a 15-minute collection cycle.** With a summary received at 08:10, the next is expected around 08:25. If the age itself stays fixed across several minutes, screen refresh needs separate investigation.

| Banner | Meaning |
| --- | --- |
| Collector current - green dot | Summary age is at or below the selected stale threshold, normally 30 minutes. |
| Collector stale - amber dot | Summary age is greater than that threshold. Previous device values and counts remain visible. |
| Collector time unavailable - grey dot | The summary generation timestamp is blank. Age displays a dash. |
| Collector time invalid - grey dot | The timestamp could not be interpreted. Age displays a dash. |
| Collector clock is ahead - grey dot | Generation time is more than five minutes in the future. Smaller positive clock differences display as zero age. |

**Source:** identifies the selected Zabbix item's display name, normally “Intune: Windows fleet summary JSON”. The source label is hidden by the widget stylesheet at viewport widths of 1,400 pixels or less. Card labels can also be shortened with an ellipsis when space is limited.

### Three different update timings

| Timing | What updates |
| --- | --- |
| Device reporting | Controlled by the Intune telemetry assignment. The dashboard does not schedule or force a device report. |
| Bridge collection | The supplied systemd timer starts a collection approximately every 15 minutes, with scheduling tolerance. |
| Widget refresh | The manifest default is 60 seconds; Zabbix owns refresh scheduling. A refresh rereads the latest stored summary and updates collector age. |

### Fields in the widget editor

| Field | Default and effect |
| --- | --- |
| Fleet summary item (automatic if blank) | Blank selects a compatible text item with key intune.windows.summary.json, preferring host “Microsoft Intune - Windows Fleet”. An explicit selection overrides automatic discovery. |
| Rows displayed | Default 10; permitted range 1-10. Changes visible rows after search/sort; it does not reduce collection or change card totals. |
| Collector stale after (minutes) | Default 30; permitted range 5-1,440. Changes the collector banner's threshold. It does not change device-report freshness or collection frequency. |

These are the three Reboot Watch-specific editor fields. General widget title, layout, refresh and dashboard editing controls are supplied by Zabbix and may depend on permissions and configuration.

<!-- pagebreak -->

## 6. Coverage, error messages and source reference

### Which devices appear?

Rows require usable script output, device ID, name, boot time and report timestamp. The collector keeps the newest usable record per immutable Intune managedDevice.id. Older valid reports can remain as Stale; invalid records and devices without usable reports are excluded.

Consequently, Windows is a reporting-population count. A fleet of over 500 enrolled devices can show 235 here. Telemetry missing = 0 does not establish that every enrolled device is reporting. Source selection can also determine which fleet summary is displayed.

Update-ring collection, cards, columns and search are disabled. The ring-disabled collector warning describes this operating mode; it does not itself indicate failure. The dashboard reports stored telemetry, not live online status.

### Messages replacing the normal display

| Message or message prefix | What it means |
| --- | --- |
| Intune fleet summary item was not found. | No compatible accessible item was selected or discovered. The message also identifies template/item setup as the relevant configuration. |
| ...no fleet telemetry has arrived yet. | A compatible item exists but has no stored history value. |
| The Intune fleet summary is invalid: ... | The newest stored value could not be decoded or parsed. The following detail identifies the JSON, compression, size or PHP-zlib issue. The error panel replaces the normal content. |
| No managed Windows devices are available. | The parsed summary contains no usable rows. This is the widget's generic empty-data label; the normal collector refuses to publish an empty usable population. |

Collector stale accompanies an older readable summary. Invalid data replaces the display with an error panel. Release 0.7.14 uses lossless compression within a 64,000-byte transport budget and 4,000,000-byte decoded bound. Failed collection/publication can leave the previous summary ageing in place.

### Where these screen rules are implemented

The [verified repository source](https://github.com/Infiltrator-Projects/Intune-Zabbix-Bridge/tree/6ef81d779365ba855c91c02bc452e184e782394e) contains the following files. Widget paths below are relative to `module/intune_reboot_watch/`.

| Source path | Responsibility |
| --- | --- |
| views/widget.view.php | Labels, cards, columns, count and footer. |
| actions/WidgetView.php | Source/history, dates and uptime colours. |
| includes/FleetSummary.php | Decoding, rows and card totals. |
| includes/TelemetryState.php | Collector age and banner states. |
| includes/WidgetForm.php | Editor fields, defaults and ranges. |
| assets/js/class.widget.js and assets/css/widget.css | Search, sorting, colours and layout. |
| src/intune_zabbix_bridge/current.py, hardened.py and collector.py | Population, telemetry, uptime and reboot rules. |
| src/intune_zabbix_bridge/transport.py | Compression and transport limits. |

Scope: the Reboot Watch widget in release 0.7.14. This guide describes the implemented behaviour; it does not change configuration, collection or reboot policy.
