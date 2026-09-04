#!/usr/bin/env node
'use strict';

const fs = require('fs');
const vm = require('vm');

const source = fs.readFileSync(
    __dirname + '/../module/intune_reboot_watch/assets/js/class.widget.js',
    'utf8'
);

if (/\bfetch\s*\(/.test(source) || /XMLHttpRequest/.test(source)) {
    throw new Error('Widget client must not open its own network transport.');
}
if (/\bsetInterval\s*\(|\bsetTimeout\s*\(/.test(source)) {
    throw new Error('Widget client must not create a competing refresh timer.');
}
for (const forbidden of ['data-ring-name', 'is-ring-', 'dataset.ringName', 'ring: row.dataset']) {
    if (source.includes(forbidden)) {
        throw new Error(`Telemetry-only widget client regained update-ring behavior: ${forbidden}`);
    }
}

class StubWidget {}
const context = {CWidget: StubWidget};
vm.createContext(context);
vm.runInContext(
    source
        + '\nthis.WidgetIntuneRebootWatch = WidgetIntuneRebootWatch;'
        + '\nthis.IntuneRebootWatchTable = IntuneRebootWatchTable;',
    context
);

const widget = new context.WidgetIntuneRebootWatch();
if (!(widget instanceof StubWidget)) {
    throw new Error('Widget client does not extend CWidget.');
}

const table = context.IntuneRebootWatchTable;

if (!table.matches({computer: 'LAB-PC-17', user: 'student@example.com'}, 'pc-17')) {
    throw new Error('Computer-name partial search failed.');
}
if (!table.matches({computer: 'LAB-PC-17', user: 'Student.Name@example.com'}, 'student.name')) {
    throw new Error('Username search is not case-insensitive.');
}
if (table.matches({computer: 'LAB-PC-17', user: 'student@example.com'}, 'teacher')) {
    throw new Error('Unrelated search unexpectedly matched.');
}
if (table.compareValues('2', '10', 'number', 'asc') >= 0) {
    throw new Error('Numeric ascending sort failed.');
}
if (table.compareValues('2', '10', 'number', 'desc') <= 0) {
    throw new Error('Numeric descending sort failed.');
}
if (table.compareValues('PC-2', 'PC-10', 'text', 'asc') >= 0) {
    throw new Error('Natural text sort failed.');
}
if (table.compareValues('', 'named-user', 'text', 'desc') <= 0) {
    throw new Error('Blank values must remain last.');
}

function stubRow(rank, computer, user, sortValues) {
    return {
        dataset: {
            sortRank: String(rank),
            computerName: computer,
            user
        },
        getAttribute(name) {
            return sortValues[name.replace('data-sort-', '')] ?? '';
        }
    };
}

const fleet = Array.from({length: 20}, (_, index) => stubRow(
    index + 1,
    `PC-${index + 1}`,
    `user-${index + 1}@example.com`,
    {'last-restart': index + 1, uptime: index + 1}
));
const sortedFleet = table.sortRows(fleet, 'last-restart', 'number', 'desc');
const firstPage = table.filterRows(sortedFleet, '').slice(0, 10);

if (firstPage.length !== 10
        || firstPage[0].dataset.computerName !== 'PC-20'
        || firstPage[9].dataset.computerName !== 'PC-11') {
    throw new Error('Sort must rank the complete fleet before applying the display limit.');
}

const searched = table.filterRows(sortedFleet, 'PC-3');
if (searched.length !== 1 || searched[0].dataset.computerName !== 'PC-3') {
    throw new Error('Search must evaluate the complete fleet rather than only visible rows.');
}

console.log('WidgetClientTest: all assertions passed.');
