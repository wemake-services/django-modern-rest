#!/usr/bin/env bash

set -euo pipefail

{
  cibuildwheel --print-build-identifiers --platform linux \
  | pyp 'json.dumps({"only": x, "os": "ubuntu-latest"})' \
  && cibuildwheel --print-build-identifiers --platform macos \
  | pyp 'json.dumps({"only": x, "os": "macos-latest"})'
} | pyp 'json.dumps(list(map(json.loads, lines)))' > /tmp/matrix
