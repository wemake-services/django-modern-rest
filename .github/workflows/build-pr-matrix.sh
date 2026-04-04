#!/usr/bin/env bash

set -euo pipefail

{
  CIBW_BUILD="cp311-*" cibuildwheel --print-build-identifiers --platform linux \
  | pyp 'json.dumps({"only": x, "os": "ubuntu-latest"})' \
  && CIBW_BUILD="cp314-*" cibuildwheel --print-build-identifiers --platform macos \
  | pyp 'json.dumps({"only": x, "os": "macos-latest"})'
} | pyp 'json.dumps(list(map(json.loads, lines)))' > /tmp/matrix
