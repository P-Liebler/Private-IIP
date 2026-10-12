#!/bin/sh
set -eu
lock_hash=$(sha256sum package-lock.json | cut -d ' ' -f 1)
stored_hash=$(cat node_modules/.private-iip-lock 2>/dev/null || true)
if [ "$lock_hash" != "$stored_hash" ]; then
    npm ci
    printf '%s\n' "$lock_hash" > node_modules/.private-iip-lock
fi
exec npm run dev
