<?php declare(strict_types = 1);

require_once __DIR__.'/../module/intune_reboot_watch/includes/FleetSummary.php';

use Modules\IntuneRebootWatch\Includes\FleetSummary;

$parser = new FleetSummary();
$raw = json_encode([
    'generated_at' => '2026-09-07T08:00:00+10:00',
    'devices' => [['computer_name' => 'PC-1', 'user' => 'élève@example.com']]
], JSON_THROW_ON_ERROR | JSON_UNESCAPED_UNICODE);
$envelope = [
    'transport' => 'intune-zabbix-zlib-v1',
    'uncompressed_bytes' => strlen($raw),
    'data' => base64_encode(gzcompress($raw, 9))
];
if ($parser->parse($raw) !== $parser->parse(json_encode($envelope, JSON_THROW_ON_ERROR))) {
    throw new RuntimeException('Compressed summary changed parsed rows or counters.');
}

function reject_transport(FleetSummary $parser, array $envelope): void {
    try {
        $parser->parse(json_encode($envelope, JSON_THROW_ON_ERROR));
    }
    catch (InvalidArgumentException) {
        return;
    }
    throw new RuntimeException('Invalid compressed summary was accepted.');
}

foreach ([
    ['transport' => 'unknown-v2'],
    ['data' => '!invalid base64!'],
    ['data' => base64_encode('not a zlib stream')],
    ['data' => substr($envelope['data'], 0, -8)],
    ['uncompressed_bytes' => 0],
    ['uncompressed_bytes' => (string) strlen($raw)],
    ['uncompressed_bytes' => strlen($raw) - 1],
    ['uncompressed_bytes' => strlen($raw) + 1],
    ['uncompressed_bytes' => 4000001],
    ['data' => []],
    ['padding' => str_repeat('x', 64000)]
] as $change) {
    reject_transport($parser, array_replace($envelope, $change));
}

// A tiny compressed stream cannot allocate an unbounded decoded value.
reject_transport($parser, array_replace($envelope, [
    'uncompressed_bytes' => 4000000,
    'data' => base64_encode(gzcompress(str_repeat('x', 4000001), 9))
]));

foreach (['{broken', 'null', '[]', '{}', json_encode($envelope, JSON_THROW_ON_ERROR)] as $invalid) {
    reject_transport($parser, array_replace($envelope, [
        'uncompressed_bytes' => strlen($invalid),
        'data' => base64_encode(gzcompress($invalid, 9))
    ]));
}

echo "SummaryTransport tests passed.\n";
