#!/bin/bash
# env.sh - konfigurasi paling minimal untuk pemula

# Target device
TARGET_IP="192.168.100.17"

# Ports (kosongkan kalau tidak dipakai)
HTTP_PORT="8080"
MQTT_PORT="1883"

# Interface untuk tshark capture
NET_IFACE="wlx1027f5cf326a"

# Folder output
LOG_DIR="./logs"
PCAP_DIR="./pcap"

# Mode: plain atau e2e
MODE="e2e"

# Payload dummy size (bytes) & interval kirim
PAYLOAD_BYTES="64"
INTERVAL_SEC="1"
TIMEOUT_MS="1200"

# Crypto settings (untuk MODE=e2e)
CIPHER="aesgcm"  # aesgcm atau chacha20poly1305
KEY_HEX="00112233445566778899aabbccddeeff00112233445566778899aabbccddeeff"
AAD="UNRAM-IOT-E2E"

# HTTP endpoint (device harus sediakan)
HTTP_SCHEME="http"
HTTP_PATH="/e2e"

# MQTT topics
MQTT_TOPIC_DATA="test/e2e/data"
MQTT_TOPIC_ACK="test/e2e/ack"
MQTT_CLIENT_ID="pc-a-e2e"
