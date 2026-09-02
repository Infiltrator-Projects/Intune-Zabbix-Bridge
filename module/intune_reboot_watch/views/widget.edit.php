<?php declare(strict_types = 1);

/** @var CView $this */
/** @var array<string, mixed> $data */

(new CWidgetFormView($data))
    ->addField(new CWidgetFieldMultiSelectItemView($data['fields']['itemid']))
    ->addField(new CWidgetFieldIntegerBoxView($data['fields']['show_lines']))
    ->addField(new CWidgetFieldIntegerBoxView($data['fields']['stale_minutes']))
    ->show();
