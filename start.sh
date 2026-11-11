#!/bin/sh
# Container entrypoint. If a persistent disk is mounted at /data (e.g. Hugging Face
# persistent storage), keep the database and finished videos there so they survive restarts.
set -e
cd "$(dirname "$0")"
if [ -d /data ] && [ -w /data ]; then
    mkdir -p /data/outputs /data/db
    if [ ! -L outputs ]; then
        cp -a outputs/. /data/outputs/ 2>/dev/null || true
        rm -rf outputs
        ln -s /data/outputs outputs
    fi
    export DONGNAE_DATA_DIR=/data/db
fi
exec python launch_app.py --host 0.0.0.0 --port "${PORT:-8503}" --no-browser
