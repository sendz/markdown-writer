#!/usr/bin/env bash
#
# Run the integration tests against a temporary headless LibreOffice.
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PORT="${MARKDOWN_WRITER_PORT:-2013}"
PIPE="/tmp/mdwriter-test-$$.pipe"
LOG="$(mktemp)"

cleanup() {
    if [ -n "${SOFFICE_PID:-}" ]; then
        kill "$SOFFICE_PID" 2>/dev/null || true
    fi
    rm -f "$PIPE" "$LOG"
}
trap cleanup EXIT

if pgrep -x soffice.bin >/dev/null 2>&1 || pgrep -x soffice >/dev/null 2>&1; then
    echo "ERROR: LibreOffice is already running. Close it before testing."
    exit 1
fi

echo "Starting headless LibreOffice (socket port $PORT) ..."
soffice --headless --norestore --nologo --nofirststartwizard \
    --accept="socket,host=localhost,port=${PORT};urp;" >"$LOG" 2>&1 &
SOFFICE_PID=$!

# Wait for the socket to accept connections.
for _ in $(seq 1 30); do
    if python3 - "$PORT" <<'PY' 2>/dev/null
import socket, sys
s = socket.socket()
s.settimeout(1)
s.connect(("localhost", int(sys.argv[1])))
s.close()
PY
    then
        break
    fi
    sleep 1
done
sleep 2

MARKDOWN_WRITER_PORT="$PORT" python3 "$ROOT/tests/uno_tests.py"
STATUS=$?

exit $STATUS
