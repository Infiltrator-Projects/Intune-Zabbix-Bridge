<?php declare(strict_types = 1);

/**
 * INTUNE — Reboot Watch dashboard controller.
 *
 * This is the only module component that talks to the Zabbix runtime API.
 * Summary parsing and freshness rules live in dependency-light helper classes
 * so their behaviour can be regression tested outside the frontend.
 */

namespace Modules\IntuneRebootWatch\Actions;

use API;
use CControllerDashboardWidgetView;
use CControllerResponseData;
use DateTimeImmutable;
use DateTimeZone;
use Modules\IntuneRebootWatch\Includes\FleetSummary;
use Modules\IntuneRebootWatch\Includes\TelemetryState;
use Modules\IntuneRebootWatch\Includes\WidgetForm;
use Throwable;

final class WidgetView extends CControllerDashboardWidgetView {

    /** Canonical trapper item written by the collector. */
    private const SUMMARY_KEY = 'intune.windows.summary.json';

    /** Prefer the conventional fleet host when automatic discovery has choices. */
    private const PREFERRED_HOST_NAME = 'Microsoft Intune - Windows Fleet';

    protected function doAction(): void {
        $item = $this->findSummaryItem();
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
            $error = _(
                'Intune fleet summary item was not found. Edit the widget and select '
                .'the text item with key "intune.windows.summary.json", or link the '
                .'Intune Zabbix Bridge template to the fleet host.'
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
                $error = _('The Intune fleet summary item exists, but has never received data.');
            }
            else {
                try {
                    $summary = (new FleetSummary())->parse(
                        (string) $history[0]['value'],
                        $this->rowLimit()
                    );
                    $rows = $this->prepareRows($summary['top']);
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
            'collector_state' => $state,
            'received_at' => $received_at,
            'stale_minutes' => $this->staleMinutes(),
            'user' => [
                'debug_mode' => $this->getDebugMode()
            ]
        ]));
    }

    /**
     * Resolve the source item deterministically:
     * 1. explicitly configured accessible text item;
     * 2. canonical key on the conventional fleet host;
     * 3. first accessible canonical-key text item.
     *
     * All reads use Zabbix APIs and therefore remain subject to the authenticated
     * frontend user's permissions.
     *
     * @return array<string, mixed>|null
     */
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
     * @param list<array<string, mixed>> $rows
     * @return list<array<string, mixed>>
     */
    private function prepareRows(array $rows): array {
        $result = [];

        foreach ($rows as $index => $row) {
            $uptime = max(0.0, (float) ($row['uptime_days'] ?? 0));

            $result[] = [
                'rank' => $index + 1,
                'computer_name' => (string) ($row['computer_name'] ?? ''),
                'user' => (string) ($row['user'] ?? ''),
                'uptime_days' => $uptime,
                'last_restart' => $this->formatIsoTime((string) ($row['last_restart'] ?? '')),
                'telemetry_collected' => $this->formatIsoTime(
                    (string) ($row['telemetry_collected'] ?? '')
                ),
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

    /**
     * Multi-select values are considered untrusted saved state even though the
     * native form normally supplies scalar item IDs.
     *
     * @return list<string>
     */
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
