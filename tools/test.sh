#!/usr/bin/env bash
set -Eeuo pipefail
readonly ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
readonly MODULE="$ROOT/module/intune_reboot_watch"
readonly MANIFEST="$MODULE/manifest.json"
readonly RELEASE_WORKFLOW="$ROOT/.github/workflows/test.yml"

for cmd in jq php node python3 bash grep awk stat; do command -v "$cmd" >/dev/null 2>&1 || { echo "ERROR: missing test command: $cmd" >&2; exit 1; }; done
readonly VERSION="$(jq -r '.version // empty' "$MANIFEST")"
[[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo "ERROR: invalid semantic version: $VERSION" >&2; exit 1; }

echo "[1/14] Manifest and release metadata"
jq -e '.id == "intune_reboot_watch" and .type == "widget" and .version != "" and .author == "Infiltrator Projects"' "$MANIFEST" >/dev/null
grep -Fq "**Release:** $VERSION" "$MODULE/README.md"
grep -Fq "## $VERSION —" "$MODULE/CHANGELOG.md"

echo "[2/14] PHP syntax"
while IFS= read -r -d '' file; do php -l "$file" >/dev/null; done < <(find "$MODULE" "$ROOT/tests" -type f -name '*.php' -print0)
echo "[3/14] JavaScript syntax"
node --check "$MODULE/assets/js/class.widget.js"
node --check "$ROOT/tests/WidgetClientTest.js"
echo "[4/14] Fleet summary regression"
php "$ROOT/tests/FleetSummaryTest.php"
echo "[5/14] Telemetry freshness regression"
php "$ROOT/tests/TelemetryStateTest.php"
echo "[6/14] WidgetView source contract"
php "$ROOT/tests/WidgetViewSourceContractTest.php"
echo "[7/14] Client trust-boundary contract"
node "$ROOT/tests/WidgetClientTest.js"
echo "[8/14] Python collector tests"
PYTHONPATH="$ROOT/src" python3 -m unittest discover -s "$ROOT/tests" -p 'test_*.py' -v
echo "[9/14] Python syntax"
PYTHONPATH="$ROOT/src" python3 -m compileall -q "$ROOT/src"
echo "[10/14] Shell/Python setup syntax"
while IFS= read -r -d '' file; do bash -n "$file"; done < <(find "$ROOT/tools" -type f -name '*.sh' -print0)
python3 -m py_compile "$ROOT/packaging/linux/import-config"

echo "[11/14] Security boundary contracts"
grep -Fq 'PathExists=/etc/intune-zabbix-bridge/import/intune-zabbix-bridge.env' "$ROOT/packaging/debian/intune-zabbix-bridge-import.path"
! grep -Rq '/home/.*Downloads\|/home/\*/Downloads' "$ROOT/packaging" || { echo 'ERROR: unsafe per-user Downloads config watcher returned.' >&2; exit 1; }
grep -Fq 'SOURCE = Path("/etc/intune-zabbix-bridge/import/intune-zabbix-bridge.env")' "$ROOT/packaging/linux/import-config"
grep -Fq 'stat.st_uid != 0' "$ROOT/packaging/linux/import-config"
grep -Fq 'stat.st_mode & 0o022' "$ROOT/packaging/linux/import-config"
trap_count="$(grep -c '^[[:space:]]*type: TRAP$' "$ROOT/zabbix/template_intune_zabbix_bridge.yaml")"
allowed_count="$(grep -c "^[[:space:]]*allowed_hosts: '127.0.0.1,::1'$" "$ROOT/zabbix/template_intune_zabbix_bridge.yaml")"
[[ "$trap_count" -gt 0 && "$allowed_count" -eq "$trap_count" ]] || { echo 'ERROR: every trapper item must restrict allowed_hosts.' >&2; exit 1; }

echo "[12/14] Portable installer"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
"$ROOT/tools/build-installer.sh" "$tmp" >/dev/null
run="$tmp/intune-zabbix-reboot-watch-${VERSION}.run"
[[ -x "$run" ]]
grep -aFq "MODULE_VERSION=\"$VERSION\"" "$run"

echo "[13/14] Debian package"
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
    [[ -x "$extract/usr/lib/intune-zabbix-bridge/import-config" ]]
    [[ -f "$extract/usr/lib/python3/dist-packages/intune_zabbix_bridge/hardened.py" ]]
    grep -Fq 'from intune_zabbix_bridge.hardened import main' "$extract/usr/bin/intune-zabbix-bridge"
    [[ -f "$extract/usr/lib/systemd/system/intune-zabbix-bridge-import.path" ]]
    [[ -f "$extract/usr/lib/systemd/system/intune-zabbix-bridge-import.service" ]]
    [[ "$(stat -c '%a' "$extract/etc/intune-zabbix-bridge/import")" == "700" ]]
    [[ ! -e "$extract/etc/intune-zabbix-bridge/bridge.env" ]]
    [[ -f "$extract/usr/share/doc/intune-zabbix-bridge/intune-zabbix-bridge.env.example" ]]
fi

echo "[14/14] Release and APT publication contracts"
grep -Fq 'APT_REPOSITORY_DISPATCH_TOKEN' "$RELEASE_WORKFLOW"
grep -Fq 'path="mirrored-packages/${filename}"' "$RELEASE_WORKFLOW"
grep -Fq 'Central APT mirror already contains exact ${filename}' "$RELEASE_WORKFLOW"
grep -Fq 'dists/alpha/main/binary-amd64/Packages.gz' "$RELEASE_WORKFLOW"
grep -Fq 'Public APT repository advertises intune-zabbix-bridge ${version} in catalogue and Packages.gz.' "$RELEASE_WORKFLOW"
if grep -R -F "$VERSION" "$ROOT/tools" "$ROOT/.github" >/dev/null; then
    echo "ERROR: current release version is hard-coded in tools or CI." >&2
    grep -R -n -F "$VERSION" "$ROOT/tools" "$ROOT/.github" >&2 || true
    exit 1
fi
rm -rf "$tmp"
trap - EXIT
printf 'All Intune-Zabbix-Bridge tests passed for %s.\n' "$VERSION"
