#!/usr/bin/env bash
# Reproducibility helper: download the canonical EPF Practices library and
# unzip it into source/ exactly as committed. The committed source/ is the
# canonical copy and is never edited; this script only documents its origin.
#
# Provenance: Internet Archive item "epf-2021-11-26",
#   EPF Practices 1.5.1.5 (2012-12-12), license EPL-1.0.
set -euo pipefail

URL="https://archive.org/download/epf-2021-11-26/Libraries/epf_practices_library_1.5.1.5_20121212.zip"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$ROOT/source"

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

echo "Downloading $URL"
curl -fSL "$URL" -o "$tmp/lib.zip"

echo "Unzipping into $DEST"
mkdir -p "$DEST"
unzip -q -o "$tmp/lib.zip" -d "$DEST"

echo "Done. $(find "$DEST" -name '*.xmi' | wc -l) .xmi files under $DEST/epf_prac_1515"
