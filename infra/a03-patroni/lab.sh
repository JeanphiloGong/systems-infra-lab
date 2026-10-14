#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
case "${1:-}" in
  up)
    : "${ETCD_BINARY:?Set ETCD_BINARY to etcd 3.5.17 absolute executable path}"
    docker run -d --name a03-etcd-local -p 127.0.0.1:22379:2379 \
      -v "$ETCD_BINARY:/usr/local/bin/etcd:ro" \
      alpine:latest /usr/local/bin/etcd --name a03 --data-dir /tmp/etcd-data \
      --listen-client-urls http://0.0.0.0:2379 \
      --advertise-client-urls http://host.docker.internal:22379
    docker compose -f compose.yaml up -d --build
    ;;
  down)
    # Only this disposable A03 stack is removed; its data is intentionally reset.
    docker compose -f compose.yaml down --volumes
    docker rm -f a03-etcd-local
    ;;
  *) echo 'usage: bash lab.sh up|down' >&2; exit 2 ;;
esac
