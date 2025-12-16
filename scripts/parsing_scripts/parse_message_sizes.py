import subprocess
import csv
from pathlib import Path
from collections import defaultdict

# =======================
# Windows-Pfade
# =======================
BASE_FOLDER = Path(r"C:\Users\marie\pqc\test_data\up_results\tls_performance\machine_1_messagesizes_test\traffic")
PCAP_DIR = BASE_FOLDER / "pqc"
OUTPUT_DIR = PCAP_DIR / "tls_stats"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# TLS Typen
TLS_TYPES = {
    1: "ClientHello",
    2: "ServerHello",
    8: "EncryptedExtensions",
    11: "Certificate",
    12: "ServerKeyExchange",
    14: "ServerHelloDone",
    15: "ClientKeyExchange",
    20: "Finished"
}

# TShark finden
def find_tshark():
    possible_paths = [
        r"C:\Program Files\Wireshark\tshark.exe",
        r"C:\Program Files (x86)\Wireshark\tshark.exe",
        "tshark.exe"  # Im PATH
    ]
    for path in possible_paths:
        try:
            result = subprocess.run([path, "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                print(f"Found TShark: {path}")
                return path
        except:
            continue
    raise FileNotFoundError("TShark not found. Please install Wireshark.")

# =======================
# PCAP verarbeiten
# =======================
def process_pcap(pcap_file: Path, tshark_path: str):
    basename = pcap_file.stem
    keylog_file = PCAP_DIR / f"keylog_{basename.replace('pcap_', '')}.txt"
    output_csv = OUTPUT_DIR / f"{basename}_tls_handshake_stats.csv"

    print(f"\nProcessing {pcap_file.name} ...")
    print(f"  Keylog: {keylog_file.name} (exists: {keylog_file.exists()})")
    
    # TShark-Befehl
    cmd = [
        tshark_path,
        "-r", str(pcap_file),
        "-Y", "tls.handshake.type",
        "-T", "fields",
        "-e", "frame.number",
        "-e", "ip.src",
        "-e", "tcp.srcport",
        "-e", "ip.dst",
        "-e", "tcp.dstport",
        "-e", "tls.handshake.type",
        "-e", "tls.handshake.length",
        "-E", "header=y",
        "-E", "separator=,",
        "-E", "quote=d",
        "-E", "occurrence=a",
        "-o", "tcp.desegment_tcp_streams:TRUE",
        "-o", "tls.desegment_ssl_records:TRUE",
        "-o", "tls.desegment_ssl_application_data:TRUE"
    ]

    if keylog_file.exists():
        cmd.extend(["-o", f"tls.keylog_file:{keylog_file}"])

    # TShark ausführen
    result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
    if result.returncode != 0:
        print(f"[ERROR] TShark failed:\n{result.stderr}")
        return

    lines = result.stdout.strip().splitlines()
    if len(lines) <= 1:
        print("[WARN] No TLS handshake packets found")
        return

    # CSV parsen
    reader = csv.DictReader(lines)
    stream_type_lengths = defaultdict(list)
    for row in reader:
        try:
            stream = int(row["tcp.srcport"])  # als Proxy für Stream-ID
            types = [int(t) for t in row["tls.handshake.type"].split(",")]
            lengths = [int(l) for l in row["tls.handshake.length"].split(",")]
        except Exception as e:
            print(f"[WARN] Skipping row due to parse error: {e}")
            continue
        for t, l in zip(types, lengths):
            stream_type_lengths[t].append((stream, l))

    # Stats berechnen
    rows = []
    for t, entries in stream_type_lengths.items():
        lengths = [l for _, l in entries]
        streams = [s for s, _ in entries]
        packets_per_stream = defaultdict(int)
        for s, _ in entries:
            packets_per_stream[s] += 1
        rows.append({
            "TLS Type": TLS_TYPES.get(t, f"Other_{t}"),
            "Num Messages": len(lengths),
            "Min Len": min(lengths),
            "Max Len": max(lengths),
            "Avg Len": round(sum(lengths)/len(lengths), 1),
            "Avg Packets": round(sum(packets_per_stream.values())/len(packets_per_stream), 2)
        })

    # Nach TLS-Typ sortieren
    type_order = [1,2,8,11,12,14,15,20]
    rows.sort(key=lambda x: type_order.index(next((k for k,v in TLS_TYPES.items() if v==x["TLS Type"]), 999)) if any(v==x["TLS Type"] for v in TLS_TYPES.values()) else 999)

    # CSV schreiben
    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["TLS Type","Num Messages","Min Len","Max Len","Avg Len","Avg Packets"])
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    print(f"[OK] Saved: {output_csv.name}")
    print(f"  Total messages: {sum(r['Num Messages'] for r in rows)}")
    print(f"  Unique streams: {len(set(s for entries in stream_type_lengths.values() for s,_ in entries))}")
    for row in rows:
        print(f"     {row['TLS Type']:20s}: {row['Num Messages']:5d} msgs, avg {row['Avg Len']:6.1f} bytes, {row['Avg Packets']:.2f} pkts/stream")

# =======================
# Hauptprogramm
# =======================
if __name__ == "__main__":
    tshark = find_tshark()
    pcap_files = sorted(PCAP_DIR.glob("*.pcap"))
    print(f"Found {len(pcap_files)} PCAP(s). Output directory: {OUTPUT_DIR}")

    for i, pcap in enumerate(pcap_files, 1):
        print(f"\n[{i}/{len(pcap_files)}]")
        try:
            process_pcap(pcap, tshark)
        except Exception as e:
            print(f"[ERROR] Failed to process {pcap.name}: {e}")
