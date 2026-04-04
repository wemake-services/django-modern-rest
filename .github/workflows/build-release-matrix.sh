#!/usr/bin/env bash

set -euo pipefail

{
  cibuildwheel --print-build-identifiers --platform linux \
  | pyp 'json.dumps({"only": x, "os": "ubuntu-latest"})' \
  && cibuildwheel --print-build-identifiers --platform linux --archs aarch64 \
  | pyp 'json.dumps({"only": x, "os": "ubuntu-24.04-arm"})' \
  && cibuildwheel --print-build-identifiers --platform macos \
  | pyp 'json.dumps({"only": x, "os": "macos-latest"})' \
  && cibuildwheel --print-build-identifiers --platform windows \
  | pyp 'json.dumps({"only": x, "os": "windows-latest"})' \
  && cibuildwheel --print-build-identifiers --platform windows --archs ARM64 \
  | pyp 'json.dumps({"only": x, "os": "windows-11-arm"})'
} | pyp 'json.dumps(list(map(json.loads, lines)))' > /tmp/matrix
