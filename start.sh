#!/bin/sh
set -eu
cd "$(dirname "$0")"
if ! command -v python3 >/dev/null 2>&1; then
    echo 'BlueTune needs Python 3.11 or newer. On ASL3 install python3 through your normal Debian package manager.' >&2
    exit 1
fi
exec python3 start.py "$@"
