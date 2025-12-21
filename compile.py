#!/usr/bin/env python3
import argparse, numpy as np, pandas as pd

WINDOW_SEC = 1

def pct(series, q):
    s = pd.to_numeric(series, errors="coerce").dropna()
    return np.nan if s.empty else float(np.percentile(s.to_numpy(), q))

def load_log(path):
    if not path:
        return None
    df = pd.read_csv(path)
    if "timestamp_ms" not in df.columns:
        return None
    df["ts"] = pd.to_datetime(df["timestamp_ms"], unit="ms", errors="coerce")
    df = df.dropna(subset=["ts"]).set_index("ts").sort_index()
    df["ok"] = pd.to_numeric(df.get("ok"), errors="coerce").fillna(0).astype(int)
    df["latency_ms"] = pd.to_numeric(df.get("latency_ms"), errors="coerce")
    df["enc_ms"] = pd.to_numeric(df.get("enc_ms"), errors="coerce").fillna(0)
    df["dec_ms"] = pd.to_numeric(df.get("dec_ms"), errors="coerce").fillna(0)
    df["payload_bytes"] = pd.to_numeric(df.get("payload_bytes"), errors="coerce")
    return df

def summarize(df, name):
    freq = f"{WINDOW_SEC}s"
    ok_df = df[df["ok"] == 1]
    out = pd.DataFrame(index=df.resample(freq).size().index)
    out[f"{name}_sent"] = df.resample(freq).size()
    out[f"{name}_ok"] = df["ok"].resample(freq).sum()
    out[f"{name}_success_rate"] = out[f"{name}_ok"] / out[f"{name}_sent"].replace(0, np.nan)
    out[f"{name}_p50"] = ok_df["latency_ms"].resample(freq).apply(lambda s: pct(s, 50))
    out[f"{name}_p95"] = ok_df["latency_ms"].resample(freq).apply(lambda s: pct(s, 95))
    out[f"{name}_p99"] = ok_df["latency_ms"].resample(freq).apply(lambda s: pct(s, 99))
    out[f"{name}_enc_mean"] = df["enc_ms"].resample(freq).mean()
    out[f"{name}_dec_mean"] = df["dec_ms"].resample(freq).mean()
    out[f"{name}_payload_mean"] = df["payload_bytes"].resample(freq).mean()
    return out

def main():
    p = argparse.ArgumentParser(description="Ringkas metrik latency E2E (pemula).")
    p.add_argument("--http-log", default="logs/http_log.csv")
    p.add_argument("--mqtt-log", default="logs/mqtt_log.csv")
    p.add_argument("-o", "--out", default="summary.csv")
    args = p.parse_args()

    dfs = []
    h = load_log(args.http_log)
    m = load_log(args.mqtt_log)

    if h is not None:
        dfs.append(summarize(h, "http"))
    if m is not None:
        dfs.append(summarize(m, "mqtt"))

    if not dfs:
        raise SystemExit("Tidak ada log yang bisa dibaca. Pastikan logs/http_log.csv atau logs/mqtt_log.csv ada.")

    out = dfs[0]
    for d in dfs[1:]:
        out = out.join(d, how="outer")

    out.sort_index().to_csv(args.out, index_label="window_start")
    print(f"[+] output: {args.out}")

if __name__ == "__main__":
    main()
