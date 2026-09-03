/**
 * Pure search/sort operations used by INTUNE — Reboot Watch.
 *
 * Keeping these operations independent of the DOM makes their behaviour
 * deterministic and directly regression-testable.
 */
const IntuneRebootWatchTable = Object.freeze({
    normaliseSearch(value) {
        return String(value ?? '').trim().toLocaleLowerCase();
    },

    matches({computer = '', user = '', ring = ''}, query) {
        const needle = this.normaliseSearch(query);

        return needle === ''
            || this.normaliseSearch(computer).includes(needle)
            || this.normaliseSearch(user).includes(needle)
            || this.normaliseSearch(ring).includes(needle);
    },

    compareValues(left, right, type, direction) {
        const left_value = String(left ?? '').trim();
        const right_value = String(right ?? '').trim();

        if (left_value === '' && right_value !== '') {
            return 1;
        }
        if (right_value === '' && left_value !== '') {
            return -1;
        }

        let result;

        if (type === 'number') {
            result = Number(left_value) - Number(right_value);
        }
        else {
            result = left_value.localeCompare(
                right_value,
                undefined,
                {numeric: true, sensitivity: 'base'}
            );
        }

        return direction === 'desc' ? -result : result;
    }
});

/**
 * INTUNE — Reboot Watch client controller.
 *
 * Zabbix owns refresh scheduling. The browser never contacts Microsoft Graph,
 * carries Graph credentials or starts a competing timer.
 */
class WidgetIntuneRebootWatch extends CWidget {

    onInitialize() {
        this._irw_search = '';
        this._irw_sort = {
            key: 'reboot-priority',
            type: 'number',
            direction: 'desc'
        };
    }

    setContents(response) {
        super.setContents(response);
        this.#activateTable();
    }

    #activateTable() {
        const root = this._body.querySelector('.irw');
        const search = root?.querySelector('[data-irw-search]');
        const table = root?.querySelector('.irw-table');

        if (root === null || search === null || table === null) {
            return;
        }

        search.value = this._irw_search;
        search.addEventListener('input', () => {
            this._irw_search = search.value;
            this.#applyTable(root);
        });

        for (const button of table.querySelectorAll('.irw-sort')) {
            button.addEventListener('click', () => {
                const same_column = this._irw_sort.key === button.dataset.sortKey;

                this._irw_sort = {
                    key: button.dataset.sortKey,
                    type: button.dataset.sortType,
                    direction: same_column
                        ? (this._irw_sort.direction === 'asc' ? 'desc' : 'asc')
                        : button.dataset.sortDefaultDirection
                };

                this.#applyTable(root);
            });
        }

        this.#applyTable(root);
    }

    #applyTable(root) {
        const table = root.querySelector('.irw-table');
        const body = table?.tBodies[0];

        if (body === undefined) {
            return;
        }

        const rows = [...body.querySelectorAll('tr.irw-data-row')];

        if (rows.length === 0) {
            return;
        }

        const query = IntuneRebootWatchTable.normaliseSearch(this._irw_search);
        const matches = rows.filter(row => IntuneRebootWatchTable.matches(
            {
                computer: row.dataset.computerName,
                user: row.dataset.user,
                ring: row.dataset.ringName
            },
            query
        ));
        const {key, type, direction} = this._irw_sort;

        matches.sort((left, right) => {
            const comparison = IntuneRebootWatchTable.compareValues(
                left.getAttribute(`data-sort-${key}`),
                right.getAttribute(`data-sort-${key}`),
                type,
                direction
            );

            return comparison !== 0
                ? comparison
                : Number(left.dataset.sortRank) - Number(right.dataset.sortRank);
        });

        for (const row of rows) {
            row.hidden = true;
        }
        for (const row of matches) {
            body.appendChild(row);
        }

        const row_limit = Math.max(1, Number(root.dataset.rowLimit) || 10);
        const visible = matches.slice(0, row_limit);

        visible.forEach((row, index) => {
            row.hidden = false;

            const rank = row.querySelector('.irw-rank');
            if (rank !== null) {
                rank.textContent = String(index + 1);
            }
        });

        let empty = body.querySelector('.irw-filter-empty');

        if (matches.length === 0) {
            if (empty === null) {
                empty = document.createElement('tr');
                empty.className = 'irw-filter-empty';

                const cell = document.createElement('td');
                cell.colSpan = 13;
                cell.textContent = root.dataset.noSearchResults;
                empty.appendChild(cell);
                body.appendChild(empty);
            }

            empty.hidden = false;
        }
        else if (empty !== null) {
            empty.hidden = true;
        }

        const count = root.querySelector('[data-irw-result-count]');
        if (count !== null) {
            count.textContent = query === ''
                ? `${visible.length} / ${rows.length}`
                : `${visible.length} / ${matches.length} (${rows.length})`;
        }

        for (const button of table.querySelectorAll('.irw-sort')) {
            const active = button.dataset.sortKey === key;
            const header = button.closest('th');

            button.setAttribute('aria-pressed', active ? 'true' : 'false');

            if (active) {
                button.dataset.sortDirection = direction;
            }
            else {
                delete button.dataset.sortDirection;
            }

            header?.setAttribute(
                'aria-sort',
                active ? (direction === 'asc' ? 'ascending' : 'descending') : 'none'
            );
        }
    }
}
