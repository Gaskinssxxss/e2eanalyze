#!/usr/bin/env python3
import argparse, json, os, time, threading
import urllib.request
import urllib.error

from crypto import Box, nonce12, b64e, b64d, now_ms

def require_paho():
    import paho.mqtt.client as mqtt
    return mqtt

def write_header(path, cols):
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            f.write(",".join(cols) + "\n")

def append_row(path, row):
    with open(path, "a", encoding="utf-8") as f:
        f.write(",".join(map(str, row)) + "\n")

def post_json(url, obj, timeout_s):
    data = json.dumps(obj).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type":"application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        raw = resp.read()
    return json.loads(raw.decode("utf-8", errors="replace"))

class AckStore:
    def __init__(self):
        self.lock = threading.Lock()
        self.by_seq = {}

    def put(self, seq, payload_bytes):
        with self.lock:
            self.by_seq[seq] = payload_bytes

    def pop(self, seq):
        with self.lock:
            return self.by_seq.pop(seq, None)

def make_payload(mode, seq, ts_send, payload_bytes, box: Box):
    dummy = os.urandom(max(0, payload_bytes))
    if mode == "plain":
        return {"v":1,"mode":"plain","seq":seq,"ts_send":ts_send,"payload_b64":b64e(dummy)}, 0
    n = nonce12()
    pt = json.dumps({"seq":seq,"ts_send":ts_send,"payload_b64":b64e(dummy)}).encode()
    t0 = now_ms()
    ct = box.enc(pt, n)
    t1 = now_ms()
    return {"v":1,"mode":"e2e","seq":seq,"nonce_b64":b64e(n),"ct_b64":b64e(ct)}, (t1 - t0)

def parse_ack(mode, seq, ts_send, resp_obj, box: Box):
    # return ok (0/1), dec_ms
    try:
        if mode == "plain":
            ok = (int(resp_obj.get("seq",-1)) == seq and int(resp_obj.get("ts_send",-2)) == ts_send)
            return 1 if ok else 0, 0
        n = b64d(resp_obj["nonce_b64"])
        ct = b64d(resp_obj["ct_b64"])
        t0 = now_ms()
        pt = box.dec(ct, n)
        t1 = now_ms()
        ack = json.loads(pt.decode(errors="replace"))
        ok = (int(ack.get("seq",-1)) == seq and int(ack.get("ts_send",-2)) == ts_send)
        return 1 if ok else 0, (t1 - t0)
    except Exception:
        return 0, 0

def main():
    p = argparse.ArgumentParser(description="Prober pemula: HTTP+MQTT, plain vs E2E payload, hitung latency via ACK.")
    p.add_argument("--ip", required=True)
    p.add_argument("--mode", choices=["plain","e2e"], default="e2e")
    p.add_argument("--payload-bytes", type=int, default=64)
    p.add_argument("--interval", type=float, default=1.0)
    p.add_argument("--timeout-ms", type=int, default=1200)
    p.add_argument("--cipher", choices=["aesgcm","chacha20poly1305"], default="aesgcm")
    p.add_argument("--key-hex", required=True)
    p.add_argument("--aad", default="")
    p.add_argument("--http-port", default="")
    p.add_argument("--http-scheme", default="http")
    p.add_argument("--http-path", default="/e2e")
    p.add_argument("--mqtt-port", default="")
    p.add_argument("--mqtt-topic-data", default="test/e2e/data")
    p.add_argument("--mqtt-topic-ack", default="test/e2e/ack")
    p.add_argument("--mqtt-client-id", default="pc-a-e2e")
    p.add_argument("--log-dir", default="./logs")
    args = p.parse_args()

    os.makedirs(args.log_dir, exist_ok=True)
    http_log = os.path.join(args.log_dir, "http_log.csv")
    mqtt_log = os.path.join(args.log_dir, "mqtt_log.csv")

    box = Box(key=bytes.fromhex(args.key_hex), cipher=args.cipher, aad=args.aad.encode())

    # prepare logs
    write_header(http_log, ["timestamp_ms","seq","mode","ok","latency_ms","payload_bytes","enc_ms","dec_ms","status"])
    write_header(mqtt_log, ["timestamp_ms","seq","mode","ok","latency_ms","payload_bytes","enc_ms","dec_ms"])

    # MQTT setup (optional)
    mqtt_client = None
    store = AckStore()

    if args.mqtt_port:
        mqtt = require_paho()
        mqtt_client = mqtt.Client(client_id=args.mqtt_client_id, clean_session=True)

        def on_message(client, userdata, msg):
            try:
                obj = json.loads(msg.payload.decode(errors="replace"))
                seq = int(obj.get("seq",-1))
                if seq >= 0:
                    store.put(seq, msg.payload)
            except Exception:
                pass

        mqtt_client.on_message = on_message
        mqtt_client.connect(args.ip, int(args.mqtt_port), keepalive=30)
        mqtt_client.subscribe(args.mqtt_topic_ack, qos=0)
        mqtt_client.loop_start()

    seq = 0
    while True:
        seq += 1
        ts_send = now_ms()
        timeout_s = max(0.2, args.timeout_ms/1000.0)

        # ===== HTTP (optional) =====
        if args.http_port:
            url = f"{args.http_scheme}://{args.ip}:{args.http_port}{args.http_path}"
            req_obj, enc_ms = make_payload(args.mode, seq, ts_send, args.payload_bytes, box)
            try:
                t1 = now_ms()
                resp = post_json(url, req_obj, timeout_s)
                ok, dec_ms = parse_ack(args.mode, seq, ts_send, resp, box)
                latency = now_ms() - ts_send if ok else ""
                append_row(http_log, [now_ms(), seq, args.mode, ok, latency, args.payload_bytes, enc_ms, dec_ms, 200])
            except urllib.error.HTTPError as e:
                append_row(http_log, [now_ms(), seq, args.mode, 0, "", args.payload_bytes, enc_ms, 0, e.code])
            except Exception:
                append_row(http_log, [now_ms(), seq, args.mode, 0, "", args.payload_bytes, enc_ms, 0, "ERR"])

        # ===== MQTT (optional) =====
        if mqtt_client:
            msg_obj, enc_ms = make_payload(args.mode, seq, ts_send, args.payload_bytes, box)
            try:
                mqtt_client.publish(args.mqtt_topic_data, json.dumps(msg_obj).encode(), qos=0, retain=False)
                deadline = now_ms() + args.timeout_ms
                ack_payload = None
                while now_ms() < deadline:
                    ack_payload = store.pop(seq)
                    if ack_payload is not None:
                        break
                    time.sleep(0.005)

                if ack_payload is None:
                    append_row(mqtt_log, [now_ms(), seq, args.mode, 0, "", args.payload_bytes, enc_ms, 0])
                else:
                    ack_obj = json.loads(ack_payload.decode(errors="replace"))
                    ok, dec_ms = parse_ack(args.mode, seq, ts_send, ack_obj, box)
                    latency = now_ms() - ts_send if ok else ""
                    append_row(mqtt_log, [now_ms(), seq, args.mode, ok, latency, args.payload_bytes, enc_ms, dec_ms])
            except Exception:
                append_row(mqtt_log, [now_ms(), seq, args.mode, 0, "", args.payload_bytes, enc_ms, 0])

        time.sleep(max(0.01, args.interval))

if __name__ == "__main__":
    main()
