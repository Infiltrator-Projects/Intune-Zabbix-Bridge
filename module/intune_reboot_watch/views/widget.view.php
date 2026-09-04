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
    $stat(
        _('Missed reboot'),
        (string) $summary['reboot_missed_devices'],
        (int) $summary['reboot_missed_devices'] > 0 ? 'is-critical' : ''
    ),
    $stat(_('Reboot current'), (string) $summary['reboot_current_devices'], 'is-good'),
    $stat(
        _('Reboot unknown'),
        (string) $summary['reboot_unknown_devices'],
        (int) $summary['reboot_unknown_devices'] > 0 ? 'is-warn' : ''
    ),
    $stat(_('Not active'), (string) $summary['reboot_not_active_devices']),
    $stat(_('Telemetry fresh'), (string) $summary['fresh_devices'], 'is-good'),
    $stat(
        _('Telemetry stale'),
        (string) $summary['stale_devices'],
        (int) $summary['stale_devices'] > 0 ? 'is-warn' : ''
    ),
    $stat(
        _('Telemetry missing'),
        (string) $summary['missing_devices'],
        (int) $summary['missing_devices'] > 0 ? 'is-critical' : ''
    ),
    $stat(
        _('Longest uptime'),
        number_format((float) $summary['max_uptime_days'], 1).' d',
        'is-accent'
    )
]))->addClass('irw-stats');

$search = (new CInput('search', null))
    ->addClass('irw-search')
    ->setAttribute('data-irw-search', '1')
    ->setAttribute('placeholder', _('Search computer or username'))
    ->setAttribute('aria-label', _('Search by computer name or username'))
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
        $sort_header(_('Reboot'), 'reboot-priority', 'number', 'desc', true),
        $sort_header(_('Due / next'), 'reboot-due', 'number', 'asc'),
        $sort_header(_('Uptime'), 'uptime', 'number', 'desc'),
        $sort_header(_('Last restart'), 'last-restart', 'number', 'desc'),
        $sort_header(_('Telemetry'), 'telemetry-status', 'text', 'asc'),
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
    $reboot = (new CSpan((string) $row['reboot_label']))
        ->addClass('irw-reboot-status')
        ->addClass('is-'.$row['reboot_state']);

    $table->addRow(
        (new CRow([
            (new CSpan((string) $row['rank']))->addClass('irw-rank'),
            (new CSpan((string) $row['computer_name']))->addClass('irw-computer'),
            (string) ($row['user'] !== '' ? $row['user'] : '—'),
            $reboot,
            (string) $row['reboot_due'],
            $uptime,
            (string) $row['last_restart'],
            $telemetry,
            (string) $row['telemetry_collected'],
            (string) $row['telemetry_age_display']
        ]))
            ->addClass('irw-data-row')
            ->addClass('is-'.$row['telemetry_status'])
            ->addClass('is-reboot-'.$row['reboot_state'])
            ->setAttribute('data-computer-name', (string) $row['computer_name'])
            ->setAttribute('data-user', (string) $row['user'])
            ->setAttribute('data-sort-rank', (string) $row['rank'])
            ->setAttribute('data-sort-computer', (string) $row['computer_name'])
            ->setAttribute('data-sort-user', (string) $row['user'])
            ->setAttribute('data-sort-reboot-priority', (string) $row['reboot_priority'])
            ->setAttribute('data-sort-reboot-due', (string) $row['reboot_due_sort'])
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
    (new CSpan(
        _('Weekly restart: ')
        .ucfirst((string) $summary['weekly_restart_day'])
        .' '.(string) $summary['weekly_restart_time']
        .' · policy start '.(string) $summary['weekly_restart_policy_start']
    )),
    (new CSpan(_('Sort/search use the complete fleet before the display limit.'))),
    (new CSpan(_('Zabbix received: ').(string) $data['received_at']))
]))->addClass('irw-footer');

$contents = (new CDiv([$health, $stats, $toolbar, $table, $footer]))
    ->addClass('irw')
    ->setAttribute('data-row-limit', (string) $row_limit)
    ->setAttribute('data-no-search-results', _('No computers or usernames match the search.'));

(new CWidgetView($data))
    ->addItem($contents)
    ->show();
