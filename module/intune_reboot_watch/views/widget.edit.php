<?php declare(strict_types = 1);

/**
 * Native Zabbix widget editor.
 *
 * Native field views keep validation, keyboard behaviour and appearance aligned
 * with built-in dashboard widgets.
 *
 * @var CView $this
 * @var array<string, mixed> $data
 */

(new CWidgetFormView($data))
    ->addField(new CWidgetFieldMultiSelectItemView($data['fields']['itemid']))
    ->addField(new CWidgetFieldIntegerBoxView($data['fields']['show_lines']))
    ->addField(new CWidgetFieldIntegerBoxView($data['fields']['stale_minutes']))
    ->show();
