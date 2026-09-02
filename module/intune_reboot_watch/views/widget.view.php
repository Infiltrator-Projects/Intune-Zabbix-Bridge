<?php declare(strict_types = 1);

/** @var CView $this */
/** @var array<string, mixed> $data */

if ($data['error'] !== null) {
    (new CWidgetView($data))
        ->addItem(
            (new CDiv([
                (new CDiv(_('INTUNE REBOOT TELEMETRY')))->addClass('irw-error-kicker'),
                (new CDiv((string) $data['error']))->addClass('irw-error-message')
            ]))
                ->addClass('irw-error')
                ->setAttribute('role', 'alert')
        )
        ->show();

    return;
}

$summary = $data['summary'];
$collector = $data['collector_state'];

$stat = static function(string $label, string $value, string $class = ''): CDiv {
    $box = (new CDiv([
        (new CDiv($value))->addClass('irw-stat-value'),
        (new CDiv($label))->addClass('irw-stat-label')
    ]))->addClass('irw-stat');

    if ($class !== '') {
        $box->addClass($class);
    }

    return $box;
};

$collector_age = $collector['age_minutes'] === null
    ? '—'
    : number_format((float) $collector['age_minutes'], 1).' min';

$health = (new CDiv([
    (new CSpan())->addClass('irw-health-dot'),
    (new CSpan((string) $collector['label']))->addClass('irw-health-label'),
    (new CSpan($collector_age))->addClass('irw-health-age'),
    (new CSpan(_('Source: ').(string) $data['item_name']))->addClass('irw-health-source')
]))
    ->addClass('irw-health')
    ->addClass('is-'.$collector['status'])
    ->setAttribute('role', 'status');

$stats = (new CDiv([
    $stat(_('Reporting'), (string) $summary['reporting_devices']),
    $stat(_('Fresh'), (string) $summary['fresh_devices'], 'is-good'),
    $stat(
        _('Stale'),
        (string) $summary['stale_devices'],
        (int) $summary['stale_devices'] > 0 ? 'is-warn' : ''
    ),
    $stat(
        _('Longest uptime'),
        number_format((float) $summary['max_uptime_days'], 1).' d',
        'is-accent'
    ),
    $stat(_('≥ 7 days'), (string) $summary['over_7_days']),
    $stat(
        _('≥ 14 days'),
        (string) $summary['over_14_days'],
        (int) $summary['over_14_days'] > 0 ? 'is-warn' : ''
    ),
    $stat(
        _('≥ 30 days'),
        (string) $summary['over_30_days'],
        (int) $summary['over_30_days'] > 0 ? 'is-critical' : ''
    )
]))->addClass('irw-stats');

$table = (new CTableInfo())
    ->addClass('irw-table')
    ->setHeader([
        '#',
        _('Computer'),
        _('User'),
        _('Uptime'),
        _('Last restart'),
        _('Telemetry collected'),
        _('Age')
    ]);

foreach ($data['rows'] as $row) {
    $uptime = (new CSpan(number_format((float) $row['uptime_days'], 1).' d'))
        ->addClass('irw-uptime')
        ->addClass('is-'.$row['severity']);

    $table->addRow([
        (string) $row['rank'],
        (new CSpan((string) $row['computer_name']))->addClass('irw-computer'),
        (string) ($row['user'] !== '' ? $row['user'] : '—'),
        $uptime,
        (string) $row['last_restart'],
        (string) $row['telemetry_collected'],
        number_format((float) $row['telemetry_age_hours'], 1).' h'
    ]);
}

if ($data['rows'] === []) {
    $table->setNoDataMessage(_('No fresh Windows reboot telemetry is available for ranking.'));
}

$footer = (new CDiv([
    (new CSpan(_('Collector threshold: ').(string) $data['stale_minutes'].' min')),
    (new CSpan(_('Zabbix received: ').(string) $data['received_at']))
]))->addClass('irw-footer');

(new CWidgetView($data))
    ->addItem(
        (new CDiv([$health, $stats, $table, $footer]))->addClass('irw')
    )
    ->show();
