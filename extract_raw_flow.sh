#!/bin/bash
set -e
source ./env.sh

PCAP_FILE="$1"
if [[ -z "$PCAP_FILE" || ! -f "$PCAP_FILE" ]]; then
  echo "Usage: $0 <file.pcapng>"
  exit 1
fi

BASE="${PCAP_FILE%.*}"
OUT_CSV="${BASE}_raw_flow.csv"

tshark -r "$PCAP_FILE" -T fields \
  -e frame.time_epoch -e frame.len -e ip.src -e ip.dst -e ip.proto \
  -e tcp.srcport -e tcp.dstport -e tcp.stream \
  -e tcp.analysis.ack_rtt -e tcp.analysis.retransmission \
  -E header=y -E separator=, > "$OUT_CSV"

echo "[+] raw_flow: $OUT_CSV"
