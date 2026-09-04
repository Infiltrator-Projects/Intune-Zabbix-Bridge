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
use Throwable;

/**
 * Read-only dashboard controller for the Intune fleet summary.
 *
 * Rendering a dashboard must never create Zabbix hosts, groups or items. The
 * package/template owns provisioning; this class only discovers an accessible
 * summary item and renders its most recent value.
 */
final class WidgetView extends CControllerDashboardWidgetView {

    private const SUMMARY_KEY = 'intune.windows.summary.json';
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
                'Intune fleet summary item was not found. Import/link the packaged '
                .'Intune Zabbix Bridge template or select a compatible text item in '
                .'the widget settings.'
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

    /** @return array<string, mixed>|null */
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
            'filter' => ['key_' => self::SUMMARY_KEY],
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

    /** @param list<array<string, mixed>> $rows */
    private function prepareRows(array $rows): array {
        $result = [];

        foreach ($rows as $index => $row) {
            $status = (string) ($row['telemetry_status'] ?? 'stale');
            if (!in_array($status, ['fresh', 'stale', 'missing'], true)) {
                $status = 'stale';
            }

            $uptime = is_numeric($row['uptime_days'] ?? null)
                ? max(0.0, (float) $row['uptime_days'])
                : null;
            $telemetry_age = is_numeric($row['telemetry_age_hours'] ?? null)
                ? max(0.0, (float) $row['telemetry_age_hours'])
                : null;
            $last_restart = (string) ($row['last_restart'] ?? '');
            $telemetry_collected = (string) ($row['telemetry_collected'] ?? '');
            $reboot_state = (string) ($row['reboot_state'] ?? 'unknown');
            if (!in_array($reboot_state, ['missed', 'current', 'unknown', 'not-active'], true)) {
                $reboot_state = 'unknown';
            }
            $reboot_due = (string) ($row['reboot_due'] ?? '');
            $reboot_priority = max(0, (int) ($row['reboot_priority'] ?? 0));
            $is_fault = $status !== 'fresh'
                || in_array($reboot_state, ['missed', 'unknown'], true);

            $result[] = [
                'rank' => $index + 1,
                'computer_name' => (string) ($row['computer_name'] ?? ''),
                'user' => (string) ($row['user'] ?? ''),
                'reboot_state' => $reboot_state,
                'reboot_label' => match ($reboot_state) {
                    'missed' => _('MISSED'),
                    'current' => _('Current'),
                    'not-active' => _('Not active'),
                    default => _('Unknown')
                },
                'reboot_due' => $this->formatIsoTime($reboot_due),
                'reboot_due_sort' => $this->isoTimestamp($reboot_due),
                'reboot_priority' => $reboot_priority,
                'uptime_days' => $uptime,
                'uptime_display' => $uptime === null ? '—' : number_format($uptime, 1).' d',
                'last_restart' => $this->formatIsoTime($last_restart),
                'last_restart_sort' => $this->isoTimestamp($last_restart),
                'telemetry_collected' => $this->formatIsoTime($telemetry_collected),
                'telemetry_collected_sort' => $this->isoTimestamp($telemetry_collected),
                'telemetry_age_hours' => $telemetry_age,
                'telemetry_age_display' => $telemetry_age === null
                    ? '—'
                    : number_format($telemetry_age, 1).' h',
                'telemetry_status' => $status,
                'telemetry_label' => match ($status) {
                    'fresh' => _('Fresh'),
                    'stale' => _('Stale'),
                    default => _('Missing')
                },
                'severity' => $status === 'missing'
                    ? 'missing'
                    : ($status === 'stale'
                        ? 'stale'
                        : ($uptime >= 30
                            ? 'critical'
                            : ($uptime >= 14 ? 'high' : ($uptime >= 7 ? 'warn' : 'ok')))),
                'is_fault' => $is_fault
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

    /** @return list<string> */
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
