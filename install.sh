#!/usr/bin/env bash
#
# Install the extension for the current user.
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

if pgrep -x soffice.bin >/dev/null 2>&1 || pgrep -x soffice >/dev/null 2>&1; then
    echo "WARNING: LibreOffice is running. Close it before installing,"
    echo "         otherwise the extension will not load until you restart it."
fi

"$ROOT/build.sh"

echo "Installing markdown-writer.oxt ..."
unopkg add -f "$ROOT/markdown-writer.oxt"

echo "Installed. Start (or restart) LibreOffice Writer to use it."
