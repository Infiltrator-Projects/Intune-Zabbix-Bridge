<?php declare(strict_types = 1);

namespace Modules\IntuneRebootWatch\Actions;

use API;
use CControllerDashboardWidgetView;
use CControllerResponseData;

final class WidgetView extends CControllerDashboardWidgetView {

    private const SUMMARY_KEY = 'intune.windows.summary.json';

    protected function doAction(): void {
        $data = [
            'name' => $this->getInput('name', $this->widget->getDefaultName()),
            'error' => null,
            'summary' => null,
            'rows' => [],
            'user' => [
                'debug_mode' => $this->getDebugMode()
            ]
        ];

        $item = $this->findSummaryItem();

        if ($item === null) {
            $data['error'] = _(
                'Intune fleet summary item was not found. Import/link the Intune Zabbix Bridge template and make sure the collector has sent data.'
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
                $data['error'] = _('Intune fleet summary item exists, but no telemetry has been received yet.');
            }
            else {
                try {
                    $summary = json_decode(
                        (string) $history[0]['value'],
                        true,
                        512,
                        JSON_THROW_ON_ERROR
                    );

                    if (!is_array($summary)) {
                        throw new \RuntimeException('Summary JSON is not an object.');
                    }

                    $data['summary'] = [
                        'reporting_devices' => (int) ($summary['reporting_devices'] ?? 0),
                        'fresh_devices' => (int) ($summary['fresh_devices'] ?? 0),
                        'stale_devices' => (int) ($summary['stale_devices'] ?? 0),
                        'max_uptime_days' => (float) ($summary['max_uptime_days'] ?? 0),
                        'over_7_days' => (int) ($summary['over_7_days'] ?? 0),
                        'over_14_days' => (int) ($summary['over_14_days'] ?? 0),
                        'over_30_days' => (int) ($summary['over_30_days'] ?? 0),
                        'generated_at' => $this->formatTime((string) ($summary['generated_at'] ?? '')),
                        'received_at' => zbx_date2str(DATE_TIME_FORMAT_SECONDS, (int) $history[0]['clock'])
                    ];

                    foreach (array_slice((array) ($summary['top'] ?? []), 0, 10) as $index => $row) {
                        if (!is_array($row)) {
                            continue;
                        }

                        $uptime = max(0.0, (float) ($row['uptime_days'] ?? 0));
                        $data['rows'][] = [
                            'rank' => $index + 1,
                            'computer_name' => (string) ($row['computer_name'] ?? ''),
                            'user' => (string) ($row['user'] ?? ''),
                            'uptime_days' => $uptime,
                            'last_restart' => $this->formatTime((string) ($row['last_restart'] ?? '')),
                            'telemetry_age_hours' => max(0.0, (float) ($row['telemetry_age_hours'] ?? 0)),
                            'severity' => $uptime >= 30 ? 'critical' : ($uptime >= 14 ? 'high' : ($uptime >= 7 ? 'warn' : 'ok'))
                        ];
                    }
                }
                catch (\Throwable $exception) {
                    $data['error'] = _('Intune fleet summary contains invalid JSON.');
                }
            }
        }

        $this->setResponse(new CControllerResponseData($data));
    }

    private function findSummaryItem(): ?array {
        $items = API::Item()->get([
            'output' => ['itemid', 'name', 'key_', 'value_type'],
            'selectHosts' => ['host', 'name'],
            'webitems' => true,
            'filter' => [
                'key_' => self::SUMMARY_KEY,
                'value_type' => ITEM_VALUE_TYPE_TEXT
            ],
            'limit' => 20
        ]);

        if ($items === []) {
            return null;
        }

        foreach ($items as $item) {
            foreach ($item['hosts'] ?? [] as $host) {
                if (($host['host'] ?? '') === 'Microsoft Intune - Windows Fleet'
                        || ($host['name'] ?? '') === 'Microsoft Intune - Windows Fleet') {
                    return $item;
                }
            }
        }

        return $items[0];
    }

    private function formatTime(string $value): string {
        if ($value === '') {
            return '—';
        }

        try {
            return (new \DateTimeImmutable($value))
                ->setTimezone(new \DateTimeZone(date_default_timezone_get()))
                ->format('d/m/Y g:i A');
        }
        catch (\Throwable $exception) {
            return $value;
        }
    }
}
