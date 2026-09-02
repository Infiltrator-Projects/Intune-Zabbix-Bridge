#!/usr/bin/env bash
set -Eeuo pipefail
readonly ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
readonly MODULE="$ROOT/module/intune_reboot_watch"
readonly MANIFEST="$MODULE/manifest.json"

for cmd in jq php node python3 bash grep; do command -v "$cmd" >/dev/null 2>&1 || { echo "ERROR: missing test command: $cmd" >&2; exit 1; }; done
readonly VERSION="$(jq -r '.version // empty' "$MANIFEST")"
[[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo "ERROR: invalid semantic version: $VERSION" >&2; exit 1; }

echo "[1/12] Manifest and release metadata"
jq -e '.id == "intune_reboot_watch" and .type == "widget" and .version != "" and .author == "Infiltrator Projects"' "$MANIFEST" >/dev/null
grep -Fq "**Release:** $VERSION" "$MODULE/README.md"
grep -Fq "## $VERSION —" "$MODULE/CHANGELOG.md"

echo "[2/12] PHP syntax"
while IFS= read -r -d '' file; do php -l "$file" >/dev/null; done < <(find "$MODULE" "$ROOT/tests" -type f -name '*.php' -print0)
echo "[3/12] JavaScript syntax"
node --check "$MODULE/assets/js/class.widget.js"
node --check "$ROOT/tests/WidgetClientTest.js"
echo "[4/12] Fleet summary regression"
php "$ROOT/tests/FleetSummaryTest.php"
echo "[5/12] Telemetry freshness regression"
php "$ROOT/tests/TelemetryStateTest.php"
echo "[6/12] WidgetView source contract"
php "$ROOT/tests/WidgetViewSourceContractTest.php"
echo "[7/12] Client trust-boundary contract"
node "$ROOT/tests/WidgetClientTest.js"
echo "[8/12] Python collector tests"
PYTHONPATH="$ROOT/src" python3 -m unittest discover -s "$ROOT/tests" -p 'test_*.py' -v
echo "[9/12] Python syntax"
PYTHONPATH="$ROOT/src" python3 -m compileall -q "$ROOT/src"
echo "[10/12] Shell/Python setup syntax"
while IFS= read -r -d '' file; do bash -n "$file"; done < <(find "$ROOT/tools" -type f -name '*.sh' -print0)
python3 -m py_compile "$ROOT/packaging/linux/config-helper" "$ROOT/src/intune_zabbix_bridge/config_gui.py"
echo "[11/12] Portable installer"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
"$ROOT/tools/build-installer.sh" "$tmp" >/dev/null
run="$tmp/intune-zabbix-reboot-watch-${VERSION}.run"
[[ -x "$run" ]]
grep -aFq "MODULE_VERSION=\"$VERSION\"" "$run"
echo "[12/12] Debian package"
if command -v dpkg-deb >/dev/null 2>&1; then
    "$ROOT/tools/build-deb.sh" "$tmp" >/dev/null
    deb="$tmp/intune-zabbix-bridge_${VERSION}_all.deb"
    [[ "$(dpkg-deb --field "$deb" Package)" == "intune-zabbix-bridge" ]]
    [[ "$(dpkg-deb --field "$deb" Version)" == "$VERSION" ]]
    [[ "$(dpkg-deb --field "$deb" Architecture)" == "all" ]]
    dpkg-deb --field "$deb" Depends | grep -Fq 'zabbix-frontend-php (>= 7.0)'
    extract="$tmp/extracted"
    dpkg-deb -x "$deb" "$extract"
    installed="$extract/usr/share/zabbix/modules/intune_reboot_watch/manifest.json"
    [[ -f "$installed" ]]
    [[ "$(jq -r '.version' "$installed")" == "$VERSION" ]]
    [[ -x "$extract/usr/bin/intune-zabbix-bridge-config" ]]
    [[ -x "$extract/usr/lib/intune-zabbix-bridge/config-helper" ]]
    [[ -f "$extract/usr/share/applications/intune-zabbix-bridge-config.desktop" ]]
    dpkg-deb --field "$deb" Depends | grep -Fq 'python3-gi'
    dpkg-deb --field "$deb" Depends | grep -Fq 'gir1.2-gtk-3.0'
    dpkg-deb --field "$deb" Depends | grep -Fq 'policykit-1'
fi
if grep -R -F "$VERSION" "$ROOT/tools" "$ROOT/.github" >/dev/null; then
    echo "ERROR: current release version is hard-coded in tools or CI." >&2
    grep -R -n -F "$VERSION" "$ROOT/tools" "$ROOT/.github" >&2 || true
    exit 1
fi
rm -rf "$tmp"
trap - EXIT
printf 'All Intune-Zabbix-Bridge tests passed for %s.\n' "$VERSION"
