set -eu
printf '%s\n' 'host replication r04_replica all scram-sha-256' >> "$PGDATA/pg_hba.conf"
