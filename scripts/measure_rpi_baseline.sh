#!/usr/bin/env bash
# measure_rpi_baseline.sh — Capture RPI performance baseline.
# Run ON the RPI (ssh tion@192.168.0.80 first), in the repo dir.
#
# Output: reports/rpi_baseline_<hostname>_<date>.txt — paste back into PR/audit.
#
# Required AFTER bootstrap + before/after any Stage 5 perf optimization
# (chunk_time_interval, asyncpg pool tuning, AutoARIMA cache).
set -euo pipefail

OUT="reports/rpi_baseline_$(hostname)_$(date +%F).txt"
mkdir -p reports
exec > >(tee "$OUT") 2>&1

echo "=== RPI Baseline Measurement — $(date -Iseconds) ==="
echo "Host: $(hostname) · $(uname -a)"
echo "RPI_NODE_ID: ${RPI_NODE_ID:-(unset)}"
echo ""

echo "--- 1. Hardware ---"
cat /proc/cpuinfo | grep -E "^Model" | head -1
echo "CPU cores: $(nproc)"
echo "Memory total: $(free -h | awk '/^Mem:/ {print $2}')"
echo "Disk free (/): $(df -h / | awk 'NR==2 {print $4 " of " $2}')"
echo "Uptime: $(uptime -p)"
echo "Load avg: $(cat /proc/loadavg)"
echo ""

echo "--- 2. Idle resource use (5s sample) ---"
echo "Memory:"
free -h | head -2
echo ""
echo "Top 5 procs by CPU:"
ps aux --sort=-%cpu | head -6
echo ""
echo "Top 5 procs by RSS:"
ps aux --sort=-rss | head -6
echo ""

echo "--- 3. Docker overhead ---"
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}" 2>&1 | head -10
echo ""
docker system df 2>&1 | head -10
echo ""

echo "--- 4. Container startup latency (cold restart) ---"
for svc in rpi-finished-pgai-db rpi-finished-reflex-app rpi-finished-forecast-scheduler; do
  if docker ps -a --format '{{.Names}}' | grep -q "^${svc}$"; then
    echo "-- $svc --"
    docker stop "$svc" >/dev/null 2>&1 || true
    t0=$(date +%s.%N)
    docker start "$svc" >/dev/null
    # Wait until container reports healthy (or running if no healthcheck)
    for i in $(seq 1 60); do
      st=$(docker inspect --format='{{.State.Health.Status}}' "$svc" 2>/dev/null || echo "no-hc")
      if [[ "$st" == "healthy" || "$st" == "no-hc" ]]; then
        t1=$(date +%s.%N)
        echo "  startup → $st in $(awk "BEGIN{printf \"%.2f\", $t1-$t0}")s"
        break
      fi
      sleep 1
    done
  fi
done
echo ""

echo "--- 5. DB response time (10 simple SELECTs) ---"
if docker ps --format '{{.Names}}' | grep -q "^rpi-finished-pgai-db$"; then
  set +e
  for i in {1..10}; do
    t0=$(date +%s.%N)
    docker exec -e PGPASSWORD="${POSTGRES_PASSWORD:-postgres}" rpi-finished-pgai-db \
      psql -U postgres -d ecoanp -tAc "SELECT COUNT(*) FROM influx_hist;" >/dev/null 2>&1
    t1=$(date +%s.%N)
    awk "BEGIN{printf \"  query %2d: %.3fs\n\", $i, $t1-$t0}"
  done
  set -e
fi
echo ""

echo "--- 6. Reflex route response time (15 routes) ---"
ROUTES=(/ /dashboard /alarms /trend /trend-enhanced-v2 /sensors /forecast /training-wizard
        /data-pipeline /scheduler /system /ai /sync /api/health /api/status)
for r in "${ROUTES[@]}"; do
  set +e
  out=$(curl -s -o /dev/null -w "  %{http_code} %{time_total}s %{size_download}B  $r\n" \
    --max-time 10 "http://localhost:14000${r}" 2>&1)
  set -e
  printf '%s' "$out"
done
echo ""

echo "--- 7. SD card / disk I/O ---"
echo "Random write (100MB):"
dd if=/dev/zero of=/tmp/baseline_io.tmp bs=1M count=100 conv=fdatasync 2>&1 | tail -1
rm -f /tmp/baseline_io.tmp
echo ""

echo "--- 8. Network egress (Cloudflare tunnel) ---"
docker logs cloudflared-tunnel --tail 20 2>&1 | grep -iE "connect|registered|error" | head -10 || \
  echo "  (cloudflared-tunnel not running or no recent logs)"
echo ""

echo "=== Baseline complete. Saved to: $OUT ==="
echo "Send this file back for analysis. Stage 5 perf targets:"
echo "  AC3 idle memory ×0.7"
echo "  AC4 forecast ≤5s"
echo "  AC5 boot ×0.5"
