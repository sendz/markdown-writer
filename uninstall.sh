#!/usr/bin/env bash
#
# Remove the extension for the current user.
#
set -euo pipefail

if pgrep -x soffice.bin >/dev/null 2>&1 || pgrep -x soffice >/dev/null 2>&1; then
    echo "WARNING: LibreOffice is running. Close it before uninstalling."
fi

echo "Removing com.sendyyeah.markdown-writer ..."
unopkg remove com.sendyyeah.markdown-writer || true

echo "Done."
