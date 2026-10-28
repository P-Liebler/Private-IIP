#!/bin/sh
set -eu
# A private tmpfs holds client configuration. Mount the public CA elsewhere so
# Docker does not create root-owned parents inside the unprivileged config dir.
test "$MC_CONFIG_DIR" = /tmp/.mc
mkdir -p "$MC_CONFIG_DIR/certs/CAs"
if [ "${S3_CA_REQUIRED:-false}" = true ]; then
    test -s /trusted-ca/root.crt
    cp /trusted-ca/root.crt "$MC_CONFIG_DIR/certs/CAs/root.crt"
fi
exec mc "$@"
