#!/bin/bash
# run.sh - jalankan sniffer + prober, stop dengan CTRL+C
set -e
source ./env.sh

mkdir -p "$LOG_DIR" "$PCAP_DIR"

TS=$(date +%Y%m%d_%H%M%S)
PCAP_FILE="$PCAP_DIR/all_traffic_$TS.pcapng"

echo "===================================="
echo "E2E Payload Latency Runner (pemula)"
echo "Target  : $TARGET_IP"
echo "Mode    : $MODE"
echo "HTTP    : $HTTP_PORT  path=$HTTP_PATH"
echo "MQTT    : $MQTT_PORT  topics=$MQTT_TOPIC_DATA / $MQTT_TOPIC_ACK"
echo "Iface   : $NET_IFACE"
echo "PCAP    : $PCAP_FILE"
echo "===================================="

FILTER=""
if [[ -n "$HTTP_PORT" && -n "$MQTT_PORT" ]]; then
  FILTER="tcp port $HTTP_PORT or tcp port $MQTT_PORT"
elif [[ -n "$HTTP_PORT" ]]; then
  FILTER="tcp port $HTTP_PORT"
elif [[ -n "$MQTT_PORT" ]]; then
  FILTER="tcp port $MQTT_PORT"
else
  FILTER="tcp"
fi

# start sniffer
echo "[*] Start tshark capture..."
sudo tshark -i "$NET_IFACE" -f "$FILTER" -w "$PCAP_FILE" &
SNIFF_PID=$!

cleanup() {
  echo
  echo "[*] Stop..."
  kill $SNIFF_PID 2>/dev/null || true
  wait $SNIFF_PID 2>/dev/null || true

  echo "[*] Extract raw_flow..."
  ./extract_raw_flow.sh "$PCAP_FILE" || true

  echo "[*] Done."
}
trap cleanup INT TERM

# start prober (HTTP+MQTT in one python)
echo "[*] Start prober..."
python3 prober.py \
  --ip "$TARGET_IP" \
  --mode "$MODE" \
  --payload-bytes "$PAYLOAD_BYTES" \
  --interval "$INTERVAL_SEC" \
  --timeout-ms "$TIMEOUT_MS" \
  --cipher "$CIPHER" \
  --key-hex "$KEY_HEX" \
  --aad "$AAD" \
  --http-port "$HTTP_PORT" \
  --http-scheme "$HTTP_SCHEME" \
  --http-path "$HTTP_PATH" \
  --mqtt-port "$MQTT_PORT" \
  --mqtt-topic-data "$MQTT_TOPIC_DATA" \
  --mqtt-topic-ack "$MQTT_TOPIC_ACK" \
  --mqtt-client-id "$MQTT_CLIENT_ID" \
  --log-dir "$LOG_DIR"
