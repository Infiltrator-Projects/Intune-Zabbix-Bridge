#!/usr/bin/env bash
set -euo pipefail

CONF_FILE="/etc/intune-zabbix-bridge/bridge.env"
BIN="/opt/intune-zabbix-bridge/venv/bin/intune-zabbix-bridge"

if [[ ! -r "${CONF_FILE}" ]]; then
  echo "Cannot read ${CONF_FILE}"
  exit 1
fi

if [[ ! -x "${BIN}" ]]; then
  echo "Bridge is not installed at ${BIN}"
  exit 1
fi

exec sudo -u intune-zabbix bash -c "set -a; source '${CONF_FILE}'; set +a; '${BIN}' --dry-run"
