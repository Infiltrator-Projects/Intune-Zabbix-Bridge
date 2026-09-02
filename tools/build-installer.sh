#!/usr/bin/env bash
set -Eeuo pipefail

readonly PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
readonly MODULE_PARENT="$PROJECT_ROOT/module"
readonly MODULE_NAME="intune_reboot_watch"
readonly MANIFEST="$MODULE_PARENT/$MODULE_NAME/manifest.json"
readonly OUTPUT_DIR="${1:-$PROJECT_ROOT/dist}"

command -v awk >/dev/null 2>&1 || { echo "ERROR: awk is required." >&2; exit 1; }
[[ -f "$MANIFEST" ]] || { echo "ERROR: manifest not found: $MANIFEST" >&2; exit 1; }
readonly VERSION="$(awk -F'"' '/^[[:space:]]*"version"[[:space:]]*:/ {print $4; exit}' "$MANIFEST")"
[[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo "ERROR: invalid manifest version." >&2; exit 1; }
readonly OUTPUT_FILE="$OUTPUT_DIR/intune-zabbix-reboot-watch-${VERSION}.run"
readonly PAYLOAD_FILE="$(mktemp)"
trap 'rm -f "$PAYLOAD_FILE"' EXIT

mkdir -p "$OUTPUT_DIR"
tar -czf "$PAYLOAD_FILE" -C "$MODULE_PARENT" "$MODULE_NAME"

cat > "$OUTPUT_FILE" <<HEAD
#!/usr/bin/env bash
set -Eeuo pipefail
readonly MODULE_VERSION="$VERSION"
HEAD

cat >> "$OUTPUT_FILE" <<'BODY'
readonly MODULE_ROOT="${ZABBIX_MODULE_ROOT:-/usr/share/zabbix/modules}"
readonly MODULE_NAME="intune_reboot_watch"
readonly PAYLOAD_MARKER="__INTUNE_REBOOT_WATCH_PAYLOAD__"
readonly SELF="$0"
stage_dir=""
backup_dir=""

fail() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
cleanup() { [[ -z "$stage_dir" || ! -d "$stage_dir" ]] || rm -rf "$stage_dir"; }
rollback() {
    local status=$?
    if (( status != 0 )) && [[ -n "$backup_dir" && -d "$backup_dir" ]] && [[ ! -d "$MODULE_ROOT/$MODULE_NAME" ]]; then
        mv "$backup_dir" "$MODULE_ROOT/$MODULE_NAME" || true
    fi
    cleanup
    exit "$status"
}
trap rollback ERR INT TERM
trap cleanup EXIT

[[ ${EUID:-$(id -u)} -eq 0 ]] || fail 'Run this installer as root.'
[[ -d "$MODULE_ROOT" ]] || fail "Zabbix module directory not found: $MODULE_ROOT"
for cmd in awk tail tar grep mktemp find chown chmod mv date; do command -v "$cmd" >/dev/null 2>&1 || fail "Required command not found: $cmd"; done
payload_line="$(awk -v marker="$PAYLOAD_MARKER" '$0 == marker {print NR + 1; exit}' "$SELF")"
[[ -n "$payload_line" ]] || fail 'Payload marker not found.'
stage_dir="$(mktemp -d "$MODULE_ROOT/.${MODULE_NAME}.install.XXXXXX")"
tail -n +"$payload_line" "$SELF" | tar -xzf - -C "$stage_dir"
candidate="$stage_dir/$MODULE_NAME"
manifest="$candidate/manifest.json"
[[ -f "$manifest" ]] || fail 'manifest.json missing from payload.'
grep -Eq '^[[:space:]]*"id"[[:space:]]*:[[:space:]]*"intune_reboot_watch"' "$manifest" || fail 'Invalid manifest id.'
escaped="${MODULE_VERSION//./\.}"
grep -Eq "^[[:space:]]*\"version\"[[:space:]]*:[[:space:]]*\"${escaped}\"" "$manifest" || fail 'Invalid manifest version.'
if command -v php >/dev/null 2>&1; then while IFS= read -r -d '' file; do php -l "$file" >/dev/null; done < <(find "$candidate" -name '*.php' -type f -print0); fi
chown -R root:root "$candidate"
find "$candidate" -type d -exec chmod 755 {} +
find "$candidate" -type f -exec chmod 644 {} +
if [[ -d "$MODULE_ROOT/$MODULE_NAME" ]]; then
    backup_dir="$MODULE_ROOT/${MODULE_NAME}.backup.$(date +%Y%m%d-%H%M%S).$$"
    mv "$MODULE_ROOT/$MODULE_NAME" "$backup_dir"
fi
mv "$candidate" "$MODULE_ROOT/$MODULE_NAME"
restorecon -RF "$MODULE_ROOT/$MODULE_NAME" >/dev/null 2>&1 || true
printf 'INTUNE — Reboot Watch %s installed.\n' "$MODULE_VERSION"
printf 'Zabbix: Administration -> General -> Modules -> Scan directory\n'
printf 'Enable the module and refresh the browser.\n'
BODY

printf '%s\n' '__INTUNE_REBOOT_WATCH_PAYLOAD__' >> "$OUTPUT_FILE"
cat "$PAYLOAD_FILE" >> "$OUTPUT_FILE"
chmod 755 "$OUTPUT_FILE"
printf 'Built %s\n' "$OUTPUT_FILE"
