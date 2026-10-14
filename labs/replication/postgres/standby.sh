set -eu
chmod 700 "$PGDATA"
if [ ! -f "$PGDATA/PG_VERSION" ]; then
    pg_basebackup -h primary -U r04_replica -D "$PGDATA" -Fp -Xs -P -R
fi
exec postgres -D "$PGDATA" -c hot_standby=on -c primary_conninfo='host=primary port=5432 user=r04_replica password=r04_replica_only application_name=r04_standby'
