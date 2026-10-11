#!/usr/bin/env bash
#
# Build the .oxt extension bundle.
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

OUT="markdown-writer.oxt"

# Items that belong inside the extension package.
PACKAGE_ITEMS=(
    META-INF
    description
    description.xml
    Addons.xcu
    Icons.xcu
    Shortcuts.xcu
    ProtocolHandler.xcu
    MarkdownWriter.xcu
    mdwriter.py
    pythonpath
)

# Regenerate the toolbar icons / image set so they stay in sync.
python3 tools/make_icons.py >/dev/null

# Every full-path declared in the manifest must exist, otherwise the extension
# installs but silently ignores missing files.
python3 - <<'PY'
import os
import re

manifest = open("META-INF/manifest.xml", encoding="utf-8").read()
paths = re.findall(r'manifest:full-path="([^"]+)"', manifest)
missing = [p for p in paths
           if p not in ("/",) and not os.path.exists(p)]
if missing:
    raise SystemExit("manifest references missing files: %s" % ", ".join(missing))
print("manifest paths OK (%d entries)" % len(paths))
PY

# Also make sure every package item exists.
for item in "${PACKAGE_ITEMS[@]}"; do
    [ -e "$item" ] || { echo "missing package item: $item"; exit 1; }
done

rm -f "$OUT"
rm -rf "$ROOT/build"

echo "Building $OUT ..."
zip -X -q -r "$OUT" "${PACKAGE_ITEMS[@]}" \
    -x '*/__pycache__/*' '*.pyc' '*.pyo'

echo "OK: $ROOT/$OUT"
