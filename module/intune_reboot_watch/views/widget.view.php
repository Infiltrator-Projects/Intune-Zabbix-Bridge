<?php declare(strict_types = 1);

/** @var CView $this */
/** @var array<string, mixed> $data */

if ($data['error'] !== null) {
    (new CWidgetView($data))
        ->addItem(
            (new CDiv((string) $data['error']))
                ->addClass('intune-reboot-watch-error')
                ->setAttribute('role', 'alert')
        )
        ->show();

    return;
}

$summary = $data['summary'];

$stat = static function(string $label, string $value, string $class = ''): CDiv {
    $box = (new CDiv([
        (new CDiv($value))->addClass('intune-reboot-watch-stat-value'),
        (new CDiv($label))->addClass('intune-reboot-watch-stat-label')
    ]))->addClass('intune-reboot-watch-stat');

    if ($class !== '') {
        $box->addClass($class);
    }

    return $box;
};

$stats = (new CDiv([
    $stat(_('Reporting'), (string) $summary['reporting_devices']),
    $stat(_('Fresh'), (string) $summary['fresh_devices'], 'is-good'),
    $stat(_('Stale'), (string) $summary['stale_devices'], ((int) $summary['stale_devices'] > 0 ? 'is-warn' : '')),
    $stat(_('Longest uptime'), number_format((float) $summary['max_uptime_days'], 1).' d', 'is-accent'),
    $stat(_('≥ 7 days'), (string) $summary['over_7_days']),
    $stat(_('≥ 14 days'), (string) $summary['over_14_days'], ((int) $summary['over_14_days'] > 0 ? 'is-warn' : '')),
    $stat(_('≥ 30 days'), (string) $summary['over_30_days'], ((int) $summary['over_30_days'] > 0 ? 'is-critical' : ''))
]))->addClass('intune-reboot-watch-stats');

$table = (new CTableInfo())
    ->addClass('intune-reboot-watch-table')
    ->setHeader([
        '#',
        _('Computer'),
        _('User'),
        _('Uptime'),
        _('Last restart'),
        _('Telemetry age')
    ]);

foreach ($data['rows'] as $row) {
    $uptime = (new CSpan(number_format((float) $row['uptime_days'], 1).' d'))
        ->addClass('intune-reboot-watch-uptime')
        ->addClass('is-'.$row['severity']);

    $table->addRow([
        (string) $row['rank'],
        (new CSpan((string) $row['computer_name']))->addClass('intune-reboot-watch-computer'),
        (string) ($row['user'] !== '' ? $row['user'] : '—'),
        $uptime,
        (string) $row['last_restart'],
        number_format((float) $row['telemetry_age_hours'], 1).' h'
    ]);
}

$footer = (new CDiv(
    _('Generated').' '.$summary['generated_at'].' · '._('Received by Zabbix').' '.$summary['received_at']
))->addClass('intune-reboot-watch-footer');

$body = (new CDiv([
    $stats,
    $table,
    $footer
]))->addClass('intune-reboot-watch');

(new CWidgetView($data))
    ->addItem($body)
    ->show();
