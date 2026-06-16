#!/usr/bin/env bash
# restore_db.sh — TimescaleDB-aware restore for ecoanp on fresh RPI.
# Follows the exact procedure from HANDOFF.md Round 2 (which proved 1st-attempt
# parallel pg_restore loses hypertable data due to TRUNCATE ONLY incompatibility).
#
# Usage:
#   ./scripts/restore_db.sh /tmp/ecoanp.dump
#
# Prereq: docker compose up -d rpi-finished-pgai-db   (container running)
set -euo pipefail

DUMP="${1:?Usage: $0 <ecoanp.dump>}"
[[ -f "$DUMP" ]] || { echo "Dump not found: $DUMP" >&2; exit 1; }

# Load .env (POSTGRES_PASSWORD only — never hardcode)
[[ -f .env ]] || { echo ".env missing. Run scripts/bootstrap_rpi.sh first." >&2; exit 1; }
set -a; . ./.env; set +a
: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD missing in .env}"

CONT="rpi-finished-pgai-db"
TS_VER="2.21.3"
# Build psql wrapper: password injected via env, never via argv (no ps leak)
PSQL=(docker exec -e "PGPASSWORD=$POSTGRES_PASSWORD" -i "$CONT" psql -U postgres)

docker ps --format '{{.Names}}' | grep -q "^${CONT}$" || \
  { echo "Container $CONT not running. Start with: docker compose up -d $CONT" >&2; exit 2; }

echo "[restore] 1/6 Dropping/recreating ecoanp on template0..."
"${PSQL[@]}" -d postgres -c "DROP DATABASE IF EXISTS ecoanp;"
"${PSQL[@]}" -d postgres -c "CREATE DATABASE ecoanp TEMPLATE template0;"

echo "[restore] 2/6 Installing TimescaleDB ${TS_VER}..."
"${PSQL[@]}" -d ecoanp -c "CREATE EXTENSION IF NOT EXISTS timescaledb WITH VERSION '${TS_VER}';"

echo "[restore] 3/6 timescaledb_pre_restore()..."
"${PSQL[@]}" -d ecoanp -c "SELECT timescaledb_pre_restore();"

echo "[restore] 4/6 pg_restore (single-thread, --no-owner --no-privileges)..."
docker cp "$DUMP" "$CONT:/tmp/ecoanp.dump"
docker exec -e "PGPASSWORD=$POSTGRES_PASSWORD" "$CONT" \
  pg_restore -U postgres -d ecoanp --no-owner --no-privileges /tmp/ecoanp.dump || \
  echo "[restore] pg_restore reported warnings (often benign for TS continuous aggs)."

echo "[restore] 5/6 timescaledb_post_restore()..."
"${PSQL[@]}" -d ecoanp -c "SELECT timescaledb_post_restore();"
docker exec "$CONT" rm -f /tmp/ecoanp.dump

echo "[restore] 6/6 Row counts (sanity check):"
for t in alarm_history influx_hist prediction_performance; do
  c=$("${PSQL[@]}" -d ecoanp -tAc "SELECT COUNT(*) FROM ${t};" 2>/dev/null || echo "ERR")
  printf "  %-30s %s\n" "$t" "$c"
done

echo "[restore] DONE. Continue with: docker compose up -d"
