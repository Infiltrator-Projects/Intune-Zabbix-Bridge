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
$row_limit = max(1, (int) $data['row_limit']);

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

$sort_header = static function(
    string $label,
    string $key,
    string $type,
    string $default_direction,
    bool $active = false
): CColHeader {
    $button = (new CButton(null, $label))
        ->addClass('irw-sort')
        ->setAttribute('data-sort-key', $key)
        ->setAttribute('data-sort-type', $type)
        ->setAttribute('data-sort-default-direction', $default_direction)
        ->setAttribute('aria-pressed', $active ? 'true' : 'false');

    if ($active) {
        $button->setAttribute('data-sort-direction', $default_direction);
    }

    return (new CColHeader($button))->setAttribute(
        'aria-sort',
        $active
            ? ($default_direction === 'asc' ? 'ascending' : 'descending')
            : 'none'
    );
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
    $stat(_('Windows'), (string) $summary['expected_devices']),
    $stat(_('One ring'), (string) $summary['one_ring_devices'], 'is-good'),
    $stat(
        _('No ring reported'),
        (string) $summary['no_ring_devices'],
        (int) $summary['no_ring_devices'] > 0 ? 'is-critical' : ''
    ),
    $stat(
        _('Multiple rings'),
        (string) $summary['multiple_ring_devices'],
        (int) $summary['multiple_ring_devices'] > 0 ? 'is-critical' : ''
    ),
    $stat(_('Telemetry'), (string) $summary['reporting_devices']),
    $stat(_('Fresh'), (string) $summary['fresh_devices'], 'is-good'),
    $stat(
        _('Stale'),
        (string) $summary['stale_devices'],
        (int) $summary['stale_devices'] > 0 ? 'is-warn' : ''
    ),
    $stat(
        _('Missing telemetry'),
        (string) $summary['missing_devices'],
        (int) $summary['missing_devices'] > 0 ? 'is-critical' : ''
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

$search = (new CInput('search', null))
    ->addClass('irw-search')
    ->setAttribute('data-irw-search', '1')
    ->setAttribute('placeholder', _('Search computer, username or update ring'))
    ->setAttribute('aria-label', _('Search by computer name, username or update ring'))
    ->setAttribute('autocomplete', 'off');

$shown_initially = min($row_limit, count($data['rows']));
$result_count = (new CSpan($shown_initially.' / '.count($data['rows'])))
    ->addClass('irw-result-count')
    ->setAttribute('data-irw-result-count', '1')
    ->setAttribute('aria-live', 'polite');

$toolbar = (new CDiv([$search, $result_count]))->addClass('irw-toolbar');

$table = (new CTableInfo())
    ->addClass('irw-table')
    ->setHeader([
        $sort_header('#', 'rank', 'number', 'asc'),
        $sort_header(_('Computer'), 'computer', 'text', 'asc'),
        $sort_header(_('User'), 'user', 'text', 'asc'),
        $sort_header(_('Update ring'), 'ring-name', 'text', 'asc'),
        $sort_header(_('Ring state'), 'ring-state', 'text', 'asc'),
        $sort_header(_('Ring reported'), 'ring-reported', 'number', 'desc'),
        $sort_header(_('Telemetry'), 'telemetry-status', 'text', 'asc'),
        $sort_header(_('Uptime'), 'uptime', 'number', 'desc', true),
        $sort_header(_('Last restart'), 'last-restart', 'number', 'desc'),
        $sort_header(_('Telemetry collected'), 'telemetry-collected', 'number', 'desc'),
        $sort_header(_('Age'), 'telemetry-age', 'number', 'desc')
    ]);

foreach ($data['rows'] as $row) {
    $uptime = (new CSpan((string) $row['uptime_display']))
        ->addClass('irw-uptime')
        ->addClass('is-'.$row['severity']);
    $telemetry = (new CSpan((string) $row['telemetry_label']))
        ->addClass('irw-telemetry-status')
        ->addClass('is-'.$row['telemetry_status']);
    $ring = (new CSpan((string) $row['ring_state_label']))
        ->addClass('irw-ring-status')
        ->addClass('is-'.$row['ring_state']);
    $ring_state_text = $row['ring_state'] === 'one'
        ? (string) $row['ring_status']
        : (string) $row['ring_state_label'];

    $table->addRow(
        (new CRow([
            (new CSpan((string) $row['rank']))->addClass('irw-rank'),
            (new CSpan((string) $row['computer_name']))->addClass('irw-computer'),
            (string) ($row['user'] !== '' ? $row['user'] : '—'),
            (string) ($row['ring_name'] !== '' ? $row['ring_name'] : '—'),
            new CDiv([$ring, new CSpan(' '.$ring_state_text)]),
            (string) $row['ring_last_reported'],
            $telemetry,
            $uptime,
            (string) $row['last_restart'],
            (string) $row['telemetry_collected'],
            (string) $row['telemetry_age_display']
        ]))
            ->addClass('irw-data-row')
            ->addClass('is-'.$row['telemetry_status'])
            ->addClass('is-ring-'.$row['ring_state'])
            ->setAttribute('data-computer-name', (string) $row['computer_name'])
            ->setAttribute('data-user', (string) $row['user'])
            ->setAttribute('data-ring-name', (string) $row['ring_name'])
            ->setAttribute('data-sort-rank', (string) $row['rank'])
            ->setAttribute('data-sort-computer', (string) $row['computer_name'])
            ->setAttribute('data-sort-user', (string) $row['user'])
            ->setAttribute('data-sort-ring-name', (string) $row['ring_name'])
            ->setAttribute('data-sort-ring-state', $ring_state_text)
            ->setAttribute('data-sort-ring-reported', (string) $row['ring_last_reported_sort'])
            ->setAttribute('data-sort-telemetry-status', (string) $row['telemetry_status'])
            ->setAttribute(
                'data-sort-uptime',
                $row['uptime_days'] === null ? '' : (string) $row['uptime_days']
            )
            ->setAttribute('data-sort-last-restart', (string) $row['last_restart_sort'])
            ->setAttribute(
                'data-sort-telemetry-collected',
                (string) $row['telemetry_collected_sort']
            )
            ->setAttribute(
                'data-sort-telemetry-age',
                $row['telemetry_age_hours'] === null
                    ? ''
                    : (string) $row['telemetry_age_hours']
            )
    );
}

if ($data['rows'] === []) {
    $table->setNoDataMessage(_('No managed Windows devices are available.'));
}

$footer = (new CDiv([
    (new CSpan(_('Ring and reboot telemetry faults are shown explicitly, never hidden.'))),
    (new CSpan(_('Collector threshold: ').(string) $data['stale_minutes'].' min')),
    (new CSpan(_('Zabbix received: ').(string) $data['received_at']))
]))->addClass('irw-footer');

$contents = (new CDiv([$health, $stats, $toolbar, $table, $footer]))
    ->addClass('irw')
    ->setAttribute('data-row-limit', (string) $row_limit)
    ->setAttribute('data-no-search-results', _('No computers, usernames or update rings match the search.'));

(new CWidgetView($data))
    ->addItem($contents)
    ->show();
