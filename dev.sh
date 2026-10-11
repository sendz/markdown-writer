#!/usr/bin/env bash
#
# Rebuild, reinstall and (optionally) launch LibreOffice Writer.
#
# Python UNO components are loaded when LibreOffice starts, so every code
# change needs a full restart of the office.
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

if pgrep -x soffice.bin >/dev/null 2>&1 || pgrep -x soffice >/dev/null 2>&1; then
    echo "ERROR: LibreOffice is running. Close it first."
    exit 1
fi

"$ROOT/build.sh"
unopkg remove com.sendyyeah.markdown-writer >/dev/null 2>&1 || true
unopkg add -f "$ROOT/markdown-writer.oxt"
echo "Extension (re)installed."

if [ "${1:-}" = "--run" ]; then
    echo "Launching LibreOffice Writer ..."
    soffice --writer &
fi
