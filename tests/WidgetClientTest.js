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

console.log('WidgetClientTest: all assertions passed.');
