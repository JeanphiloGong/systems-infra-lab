#!/bin/sh
set -eu
cluster=$(pg_controldata "$PGDATA" | awk '/Database system identifier/ {print $NF}')
directory=/archive/$cluster
mkdir -p "$directory"
chmod 777 "$directory"
destination=$directory/$2
if test -f "$destination"; then
    cmp "$1" "$destination"
else
    cp "$1" "$destination.tmp"
    chmod 644 "$destination.tmp"
    mv "$destination.tmp" "$destination"
fi
