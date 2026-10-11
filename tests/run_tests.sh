#!/usr/bin/env bash
#
# Run the test suite.  Pure Python tests run first, then the UNO integration
# tests run against a temporary headless LibreOffice.
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PORT="${MARKDOWN_WRITER_PORT:-2013}"
LOG="$(mktemp)"
STATUS=0

echo "### pure unit tests ###"
python3 "$ROOT/tests/test_live_text.py" || STATUS=1
python3 "$ROOT/tests/test_md2html.py" || STATUS=1

if pgrep -x soffice.bin >/dev/null 2>&1 || pgrep -x soffice >/dev/null 2>&1; then
    echo "ERROR: LibreOffice is already running. Close it before testing."
    exit 1
fi

cleanup() {
    if [ -n "${SOFFICE_PID:-}" ]; then
        kill "$SOFFICE_PID" 2>/dev/null || true
    fi
    rm -f "$LOG"
}
trap cleanup EXIT

echo
echo "### starting headless LibreOffice (socket port $PORT) ###"
soffice --headless --norestore --nologo --nofirststartwizard \
    --accept="socket,host=localhost,port=${PORT};urp;" >"$LOG" 2>&1 &
SOFFICE_PID=$!

for _ in $(seq 1 30); do
    if python3 - "$PORT" <<'PY' 2>/dev/null
import socket, sys
s = socket.socket(); s.settimeout(1)
s.connect(("localhost", int(sys.argv[1]))); s.close()
PY
    then
        break
    fi
    sleep 1
done
sleep 2

echo
echo "### UNO integration tests ###"
MARKDOWN_WRITER_PORT="$PORT" python3 "$ROOT/tests/uno_tests.py" || STATUS=1
echo
MARKDOWN_WRITER_PORT="$PORT" python3 "$ROOT/tests/test_live_integration.py" || STATUS=1

exit $STATUS
