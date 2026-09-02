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
vm.runInContext(source + '\nthis.WidgetIntuneRebootWatch = WidgetIntuneRebootWatch;', context);

const widget = new context.WidgetIntuneRebootWatch();
if (!(widget instanceof StubWidget)) {
    throw new Error('Widget client does not extend CWidget.');
}

console.log('WidgetClientTest: all assertions passed.');
