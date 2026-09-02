<?php declare(strict_types = 1);

namespace Modules\IntuneRebootWatch\Actions;

use API;
use CControllerDashboardWidgetView;
use CControllerResponseData;
use DateTimeImmutable;
use DateTimeZone;
use Modules\IntuneRebootWatch\Includes\FleetSummary;
use Modules\IntuneRebootWatch\Includes\TelemetryState;
use Modules\IntuneRebootWatch\Includes\WidgetForm;
use RuntimeException;
use Throwable;

final class WidgetView extends CControllerDashboardWidgetView {

    private const SUMMARY_KEY = 'intune.windows.summary.json';
    private const PREFERRED_HOST_NAME = 'Microsoft Intune - Windows Fleet';
    private const PREFERRED_GROUP_NAME = 'Microsoft Intune';

    protected function doAction(): void {
        $configured = $this->normaliseItemIds($this->fields_values['itemid'] ?? []);
        $bootstrap_error = null;

        $item = $this->findSummaryItem();

        /*
         * A freshly installed package should not require the operator to import
         * a template and hand-create a trapper host before the widget can work.
         * When the widget is using automatic source selection, bootstrap the
         * small Zabbix-side data model through Zabbix's own API. This remains
         * permission-aware and does not touch the database directly.
         */
        if ($item === null && $configured === []) {
            try {
                $this->ensureFleetDataModel();
                $item = $this->findSummaryItem();
            }
            catch (Throwable $exception) {
                $bootstrap_error = $exception->getMessage();
            }
        }

        $error = null;
        $summary = null;
        $rows = [];
        $state = [
            'status' => 'unknown',
            'age_minutes' => null,
            'label' => _('Collector state unknown')
        ];
        $received_at = '—';

        if ($item === null) {
            $error = $bootstrap_error !== null
                ? _('The Intune fleet data model could not be created automatically: ').$bootstrap_error
                : _(
                    'Intune fleet summary item was not found. Edit the widget and select '
                    .'a compatible text item, or use an account permitted to create the '
                    .'automatic Microsoft Intune fleet host and trapper items.'
                );
        }
        else {
            $history = API::History()->get([
                'output' => ['clock', 'value'],
                'history' => ITEM_VALUE_TYPE_TEXT,
                'itemids' => [(string) $item['itemid']],
                'sortfield' => 'clock',
                'sortorder' => ZBX_SORT_DOWN,
                'limit' => 1
            ]);

            if ($history === []) {
                $error = _(
                    'INTUNE — Reboot Watch is installed and its Zabbix data channel is ready, '
                    .'but no fleet telemetry has arrived yet. Configure/start the '
                    .'Intune-Zabbix-Bridge collector.'
                );
            }
            else {
                try {
                    $summary = (new FleetSummary())->parse(
                        (string) $history[0]['value'],
                        $this->rowLimit()
                    );
                    $rows = $this->prepareRows($summary['devices']);
                    $state = (new TelemetryState())->evaluate(
                        (string) $summary['generated_at'],
                        new DateTimeImmutable('now', new DateTimeZone('UTC')),
                        $this->staleMinutes()
                    );
                    $received_at = zbx_date2str(
                        DATE_TIME_FORMAT_SECONDS,
                        (int) $history[0]['clock']
                    );
                }
                catch (Throwable $exception) {
                    $error = _('The Intune fleet summary is invalid: ').$exception->getMessage();
                }
            }
        }

        $this->setResponse(new CControllerResponseData([
            'name' => $this->getInput('name', $this->widget->getDefaultName()),
            'error' => $error,
            'item_name' => (string) ($item['name'] ?? ''),
            'summary' => $summary,
            'rows' => $rows,
            'row_limit' => $this->rowLimit(),
            'collector_state' => $state,
            'received_at' => $received_at,
            'stale_minutes' => $this->staleMinutes(),
            'user' => [
                'debug_mode' => $this->getDebugMode()
            ]
        ]));
    }

    private function findSummaryItem(): ?array {
        $configured = $this->normaliseItemIds($this->fields_values['itemid'] ?? []);

        if ($configured !== []) {
            $items = API::Item()->get([
                'output' => ['itemid', 'name', 'key_', 'value_type'],
                'itemids' => $configured,
                'webitems' => true,
                'preservekeys' => false
            ]);

            foreach ($items as $item) {
                if ((int) ($item['value_type'] ?? -1) === ITEM_VALUE_TYPE_TEXT) {
                    return $item;
                }
            }

            return null;
        }

        $items = API::Item()->get([
            'output' => ['itemid', 'name', 'key_', 'value_type'],
            'selectHosts' => ['host', 'name'],
            'webitems' => true,
            'filter' => [
                'key_' => self::SUMMARY_KEY
            ],
            'limit' => 50
        ]);

        $eligible = array_values(array_filter(
            $items,
            static fn(array $item): bool =>
                (int) ($item['value_type'] ?? -1) === ITEM_VALUE_TYPE_TEXT
                && (string) ($item['key_'] ?? '') === self::SUMMARY_KEY
        ));

        foreach ($eligible as $item) {
            foreach ((array) ($item['hosts'] ?? []) as $host) {
                if ((string) ($host['host'] ?? '') === self::PREFERRED_HOST_NAME
                        || (string) ($host['name'] ?? '') === self::PREFERRED_HOST_NAME) {
                    return $item;
                }
            }
        }

        return $eligible[0] ?? null;
    }

    /**
     * Create the small Zabbix-side trapper model needed by the collector.
     *
     * This is intentionally idempotent and uses only public Zabbix APIs. If the
     * current frontend user cannot create host groups/hosts/items, the API call
     * fails and the widget reports that rather than bypassing Zabbix security.
     */
    private function ensureFleetDataModel(): void {
        $groupid = $this->ensureHostGroup();
        $hostid = $this->ensureFleetHost($groupid);

        $existing = API::Item()->get([
            'output' => ['itemid', 'key_'],
            'hostids' => [$hostid],
            'preservekeys' => false
        ]);

        $existing_keys = [];
        foreach ($existing as $item) {
            $existing_keys[(string) ($item['key_'] ?? '')] = true;
        }

        $items = [];
        foreach ($this->fleetItemDefinitions() as $definition) {
            if (isset($existing_keys[$definition['key_']])) {
                continue;
            }

            $items[] = ['hostid' => $hostid] + $definition;
        }

        if ($items !== []) {
            $result = API::Item()->create($items);
            if ($result === false) {
                throw new RuntimeException(
                    'Zabbix rejected creation of one or more Intune trapper items.'
                );
            }
        }
    }

    private function ensureHostGroup(): string {
        $groups = API::HostGroup()->get([
            'output' => ['groupid', 'name'],
            'filter' => ['name' => self::PREFERRED_GROUP_NAME],
            'editable' => true,
            'limit' => 1
        ]);

        if ($groups !== []) {
            return (string) $groups[0]['groupid'];
        }

        $created = API::HostGroup()->create([
            'name' => self::PREFERRED_GROUP_NAME
        ]);

        if ($created === false || empty($created['groupids'][0])) {
            throw new RuntimeException(
                'Zabbix did not allow creation of the Microsoft Intune host group.'
            );
        }

        return (string) $created['groupids'][0];
    }

    private function ensureFleetHost(string $groupid): string {
        $hosts = API::Host()->get([
            'output' => ['hostid', 'host', 'name'],
            'filter' => ['host' => self::PREFERRED_HOST_NAME],
            'editable' => true,
            'limit' => 1
        ]);

        if ($hosts !== []) {
            return (string) $hosts[0]['hostid'];
        }

        $created = API::Host()->create([
            'host' => self::PREFERRED_HOST_NAME,
            'name' => self::PREFERRED_HOST_NAME,
            'status' => HOST_STATUS_MONITORED,
            'groups' => [
                ['groupid' => $groupid]
            ]
        ]);

        if ($created === false || empty($created['hostids'][0])) {
            throw new RuntimeException(
                'Zabbix did not allow creation of the Microsoft Intune fleet host.'
            );
        }

        return (string) $created['hostids'][0];
    }

    /**
     * @return list<array<string, mixed>>
     */
    private function fleetItemDefinitions(): array {
        return [
            [
                'name' => 'Intune: Windows reporting devices',
                'key_' => 'intune.windows.reporting.count',
                'type' => ITEM_TYPE_TRAPPER,
                'value_type' => ITEM_VALUE_TYPE_UINT64
            ],
            [
                'name' => 'Intune: Windows fresh telemetry devices',
                'key_' => 'intune.windows.fresh.count',
                'type' => ITEM_TYPE_TRAPPER,
                'value_type' => ITEM_VALUE_TYPE_UINT64
            ],
            [
                'name' => 'Intune: Windows stale telemetry devices',
                'key_' => 'intune.windows.stale.count',
                'type' => ITEM_TYPE_TRAPPER,
                'value_type' => ITEM_VALUE_TYPE_UINT64
            ],
            [
                'name' => 'Intune: Maximum Windows uptime',
                'key_' => 'intune.windows.max.uptime.days',
                'type' => ITEM_TYPE_TRAPPER,
                'value_type' => ITEM_VALUE_TYPE_FLOAT,
                'units' => 'd'
            ],
            [
                'name' => 'Intune: Windows uptime >= 7 days',
                'key_' => 'intune.windows.uptime.over7.count',
                'type' => ITEM_TYPE_TRAPPER,
                'value_type' => ITEM_VALUE_TYPE_UINT64
            ],
            [
                'name' => 'Intune: Windows uptime >= 14 days',
                'key_' => 'intune.windows.uptime.over14.count',
                'type' => ITEM_TYPE_TRAPPER,
                'value_type' => ITEM_VALUE_TYPE_UINT64
            ],
            [
                'name' => 'Intune: Windows uptime >= 30 days',
                'key_' => 'intune.windows.uptime.over30.count',
                'type' => ITEM_TYPE_TRAPPER,
                'value_type' => ITEM_VALUE_TYPE_UINT64
            ],
            [
                'name' => 'Intune: Last telemetry collection',
                'key_' => 'intune.windows.last.collection.epoch',
                'type' => ITEM_TYPE_TRAPPER,
                'value_type' => ITEM_VALUE_TYPE_UINT64,
                'units' => 'unixtime'
            ],
            [
                'name' => 'Intune: Top 10 longest uptime',
                'key_' => 'intune.windows.top10',
                'type' => ITEM_TYPE_TRAPPER,
                'value_type' => ITEM_VALUE_TYPE_TEXT
            ],
            [
                'name' => 'Intune: Windows fleet summary JSON',
                'key_' => self::SUMMARY_KEY,
                'type' => ITEM_TYPE_TRAPPER,
                'value_type' => ITEM_VALUE_TYPE_TEXT
            ]
        ];
    }

    private function prepareRows(array $rows): array {
        $result = [];

        foreach ($rows as $index => $row) {
            $uptime = max(0.0, (float) ($row['uptime_days'] ?? 0));
            $last_restart = (string) ($row['last_restart'] ?? '');
            $telemetry_collected = (string) ($row['telemetry_collected'] ?? '');

            $result[] = [
                'rank' => $index + 1,
                'computer_name' => (string) ($row['computer_name'] ?? ''),
                'user' => (string) ($row['user'] ?? ''),
                'uptime_days' => $uptime,
                'last_restart' => $this->formatIsoTime($last_restart),
                'last_restart_sort' => $this->isoTimestamp($last_restart),
                'telemetry_collected' => $this->formatIsoTime($telemetry_collected),
                'telemetry_collected_sort' => $this->isoTimestamp($telemetry_collected),
                'telemetry_age_hours' => max(
                    0.0,
                    (float) ($row['telemetry_age_hours'] ?? 0)
                ),
                'severity' => $uptime >= 30
                    ? 'critical'
                    : ($uptime >= 14 ? 'high' : ($uptime >= 7 ? 'warn' : 'ok'))
            ];
        }

        return $result;
    }

    private function formatIsoTime(string $value): string {
        if (trim($value) === '') {
            return '—';
        }

        try {
            return (new DateTimeImmutable($value))
                ->setTimezone(new DateTimeZone(date_default_timezone_get()))
                ->format('d/m/Y g:i:s A');
        }
        catch (Throwable) {
            return $value;
        }
    }

    private function isoTimestamp(string $value): int {
        if (trim($value) === '') {
            return 0;
        }

        try {
            return (new DateTimeImmutable($value))->getTimestamp();
        }
        catch (Throwable) {
            return 0;
        }
    }

    private function normaliseItemIds(mixed $value): array {
        $values = is_array($value) ? $value : [$value];
        $ids = [];

        foreach ($values as $candidate) {
            if (is_scalar($candidate) && (string) $candidate !== '') {
                $ids[] = (string) $candidate;
            }
        }

        return array_values(array_unique($ids));
    }

    private function rowLimit(): int {
        $configured = (int) (
            $this->fields_values['show_lines'] ?? WidgetForm::DEFAULT_ROW_LIMIT
        );

        return max(
            WidgetForm::MINIMUM_ROW_LIMIT,
            min(WidgetForm::MAXIMUM_ROW_LIMIT, $configured)
        );
    }

    private function staleMinutes(): int {
        $configured = (int) (
            $this->fields_values['stale_minutes'] ?? WidgetForm::DEFAULT_STALE_MINUTES
        );

        return max(
            WidgetForm::MINIMUM_STALE_MINUTES,
            min(WidgetForm::MAXIMUM_STALE_MINUTES, $configured)
        );
    }
}
