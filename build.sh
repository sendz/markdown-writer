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
    mdwriter.py
    pythonpath
)

rm -f "$OUT"
rm -rf "$ROOT/build"

echo "Building $OUT ..."
zip -X -q -r "$OUT" "${PACKAGE_ITEMS[@]}" \
    -x '*/__pycache__/*' '*.pyc' '*.pyo'

echo "OK: $ROOT/$OUT"
