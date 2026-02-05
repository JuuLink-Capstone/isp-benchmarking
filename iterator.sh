#!/bin/bash
set -euo pipefail

############################
# CONFIGURATION
############################
SERVER="165.227.20.120"
BIND_IP="192.168.1.251"
IFACE="enp1s0"

DURATION=300             # seconds per test
OMIT=30                 # TCP slow-start omit
ITER_START=1

LOGDIR="./tests/log"
META_LOG="${LOGDIR}/metadata.log"
TCP_LOG="${LOGDIR}/tcp.log"
UDP_LOG="${LOGDIR}/udp.log"
FPING_LOG="${LOGDIR}/fping.log"

cleanup_logs() {
    rm -f \
        "$TCP_LOG" \
        "$UDP_LOG" \
        "$FPING_LOG" \
        "$META_LOG"
    echo "Logs cleaned."
}

if [[ "${1:-}" == "clean" ]]; then
    cleanup_logs
    exit 0
fi

# UDP rate ladder (space-separated)
UDP_RATES=("100M" "300M" "600M" "900M")

# fping parameters
FPING_INTERVAL_MS=100   # inter-packet gap
FPING_PERIOD_MS=100     # per-host period

############################
# SETUP
############################
mkdir -p "$LOGDIR"

ITER=$ITER_START
FPING_PID=""

cleanup() {
    echo "[$(date --iso-8601=seconds)] Caught Ctrl+C, shutting down" | tee -a "$META_LOG"

    if [[ -n "${FPING_PID}" ]] && kill -0 "$FPING_PID" 2>/dev/null; then
        kill "$FPING_PID"
        wait "$FPING_PID" 2>/dev/null || true
    fi

    echo "[$(date --iso-8601=seconds)] ethtool post-run" >> "$META_LOG"
    ethtool -S "$IFACE" >> "$META_LOG" 2>&1

    exit 0
}

trap cleanup SIGINT SIGTERM

############################
# METADATA (PRE)
############################
echo "========================================" >> "$META_LOG"
echo "Run start: $(date --iso-8601=seconds)" >> "$META_LOG"
echo "Server: $SERVER" >> "$META_LOG"
echo "Bind IP: $BIND_IP" >> "$META_LOG"
echo "Interface: $IFACE" >> "$META_LOG"
echo "----------------------------------------" >> "$META_LOG"
echo "ethtool pre-run" >> "$META_LOG"
ethtool -S "$IFACE" >> "$META_LOG" 2>&1
echo "========================================" >> "$META_LOG"

############################
# BACKGROUND FPING
############################
fping -l -e -D -i "$FPING_INTERVAL_MS" "$SERVER" >> "$FPING_LOG" 2>&1 &
FPING_PID=$!

############################
# MAIN LOOP
############################

RETRIES=3
SLEEP_BETWEEN=5  # seconds

while true; do
    TS=$(date +"%Y%m%d_%H%M%S")

    ########################
    # TCP TESTS (APPEND)
    ########################
    for MODE in "C2S" "S2C" "BIDIR"; do
        attempt=1
        success=0
        while [ $attempt -le $RETRIES ]; do
            case $MODE in
                C2S)
                    echo "========== ITER $ITER | $TS | TCP C2S ==========" >> "$TCP_LOG"
                    iperf3 -c "$SERVER" -t "$DURATION" --omit "$OMIT" -B "$BIND_IP" >> "$TCP_LOG" 2>&1
                    ;;
                S2C)
                    echo "========== ITER $ITER | $TS | TCP S2C ==========" >> "$TCP_LOG"
                    iperf3 -c "$SERVER" -t "$DURATION" --omit "$OMIT" -R -B "$BIND_IP" >> "$TCP_LOG" 2>&1
                    ;;
                BIDIR)
                    echo "========== ITER $ITER | $TS | TCP BIDIR ==========" >> "$TCP_LOG"
                    iperf3 -c "$SERVER" -t "$DURATION" --omit "$OMIT" --bidir -B "$BIND_IP" >> "$TCP_LOG" 2>&1
                    ;;
            esac

            if [ $? -eq 0 ]; then
                success=1
                break
            else
                echo "Iteration $ITER, mode $MODE failed on attempt $attempt, retrying in $SLEEP_BETWEEN sec..." >> "$TCP_LOG"
                sleep $SLEEP_BETWEEN
                attempt=$((attempt + 1))
            fi
        done

        if [ $success -eq 0 ]; then
            echo "Iteration $ITER, mode $MODE failed after $RETRIES attempts, skipping..." >> "$TCP_LOG"
        fi
        sleep $SLEEP_BETWEEN
    done

    ########################
    # UDP RATE LADDER
    ########################
    for RATE in "${UDP_RATES[@]}"; do
        attempt=1
        success=0
        while [ $attempt -le $RETRIES ]; do
            echo "========== ITER $ITER | $TS | UDP $RATE ==========" >> "$UDP_LOG"
            iperf3 -c "$SERVER" -t "$DURATION" -u -b "$RATE" -B "$BIND_IP" >> "$UDP_LOG" 2>&1

            if [ $? -eq 0 ]; then
                success=1
                break
            else
                echo "Iteration $ITER, UDP $RATE failed on attempt $attempt, retrying in $SLEEP_BETWEEN sec..." >> "$UDP_LOG"
                sleep $SLEEP_BETWEEN
                attempt=$((attempt + 1))
            fi
        done

        if [ $success -eq 0 ]; then
            echo "Iteration $ITER, UDP $RATE failed after $RETRIES attempts, skipping..." >> "$UDP_LOG"
        fi
        sleep $SLEEP_BETWEEN
    done

    ((ITER++))
done
