#!/usr/bin/env bash

set -euo pipefail

export CIBW_ARCHS_LINUX='x86_64'
export CIBW_ARCHS_MACOS='x86_64 arm64'
export CIBW_ARCHS_WINDOWS='AMD64'

{
  cibuildwheel --print-build-identifiers --platform linux \
  | pyp 'json.dumps({"only": x, "os": "ubuntu-latest"})' \
  && cibuildwheel --print-build-identifiers --platform linux --archs aarch64 \
  | pyp 'json.dumps({"only": x, "os": "ubuntu-24.04-arm"})' \
  && cibuildwheel --print-build-identifiers --platform macos \
  | pyp 'json.dumps({"only": x, "os": "macos-latest"})' \
  && cibuildwheel --print-build-identifiers --platform windows \
  | pyp 'json.dumps({"only": x, "os": "windows-latest"})'
} | pyp 'json.dumps(list(map(json.loads, lines)))' > /tmp/matrix
