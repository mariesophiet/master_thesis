import pandas as pd
import glob
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib

# ============================================================
# Algorithmuslisten
# ============================================================

PQ_ALGOS = [
    "falcon512", "falcon1024",
    "MLDSA44", "MLDSA65", "MLDSA87",
    "sphincssha2128fsimple", "sphincssha2128ssimple"
]

CLASSIC_ALGOS = [
    "RSA_2048",
    "RSA_3072",
    "RSA_4096",
    "prime256v1",
    "secp384r1",
    "secp521r1"
]

# Farben nur nach Kryptoklasse
CLASSIC_COLOR = "#1f77b4"  # blau
PQ_COLOR = "#d62728"       # rot

# Marker nach Familie
MARKER_MAP = {
    "RSA": "s",
    "ECC": "o",
    "falcon": "^",
    "MLDSA": "D",
    "sphincs": "X"
}

def get_marker(algo: str) -> str:
    if algo.startswith("RSA"):
        return MARKER_MAP["RSA"]
    if algo.startswith("prime") or algo.startswith("secp"):
        return MARKER_MAP["ECC"]
    if algo.startswith("falcon"):
        return MARKER_MAP["falcon"]
    if algo.startswith("MLDSA"):
        return MARKER_MAP["MLDSA"]
    if algo.startswith("sphincs"):
        return MARKER_MAP["sphincs"]
    return "o"

# ============================================================
# Pfade
# ============================================================

SCRIPT_DIR = Path(__file__).resolve().parent

BASE_FOLDER_CLASSIC = (
    SCRIPT_DIR / ".." / ".." /
    "test_data" / "results" / "tls_performance" /
    "machine_1" / "handshake_results" / "classic"
)

BASE_FOLDER_PQ = (
    SCRIPT_DIR / ".." / ".." /
    "test_data" / "results" / "tls_performance" /
    "machine_1" / "handshake_results" / "pqc"
)

BASE_FOLDER_STATS_CLASSIC = (
    SCRIPT_DIR / ".." / ".." /
    "test_data" / "up_results" / "tls_performance" /
    "machine_1_messagesizes_test" / "traffic" / "classic" / "tls_stats"
)

BASE_FOLDER_STATS_PQ = (
    SCRIPT_DIR / ".." / ".." /
    "test_data" / "up_results" / "tls_performance" /
    "machine_1_messagesizes_test" / "traffic" / "pqc" / "tls_stats"
)

SAVE_PATH_SCATTER = Path(
    r"C:\Users\marie\OneDrive\Documents\Fernuni\Masterarbeit\Plots\Szenario_1_Raspi"
    r"\sc1_certsize_vs_throughput_mlkem1024_family_markers.png"
)

# ============================================================
# Helper-Funktionen unverändert
# ============================================================

def load_cert_sizes_classic(stats_base_folder):
    rows = []
    for algo in CLASSIC_ALGOS:
        pattern = stats_base_folder / f"pcap_*_{algo}_tls_handshake_stats.csv"
        files = glob.glob(str(pattern))
        if not files:
            continue
        df = pd.read_csv(files[0])
        cert_row = df[df["TLS Type"] == "Certificate"]
        if cert_row.empty:
            continue
        rows.append({
            "Signing Algorithm": algo,
            "Cert Size (KB)": cert_row["Avg Len"].iloc[0] / 1024
        })
    return pd.DataFrame(rows)

def load_cert_sizes_mlkem1024(stats_base_folder, kem):
    rows = []
    for algo in PQ_ALGOS:
        pattern = stats_base_folder / f"pcap_*_{algo}_{kem}_tls_handshake_stats.csv"
        files = glob.glob(str(pattern))
        if not files:
            continue
        df = pd.read_csv(files[0])
        cert_row = df[df["TLS Type"] == "Certificate"]
        if cert_row.empty:
            continue
        rows.append({
            "Signing Algorithm": algo,
            "Cert Size (KB)": cert_row["Avg Len"].iloc[0] / 1024
        })
    return pd.DataFrame(rows)

def load_median_handshake_throughput_classic():
    rows = []
    files = glob.glob(str(BASE_FOLDER_CLASSIC / "classic_results_run_*.csv"))
    if not files:
        return pd.DataFrame()
    dfs = []
    for f in files:
        df = pd.read_csv(f)
        df = df[df["Reused Session ID"].isna()]
        df = df[df["Ciphersuite"] == "TLS_AES_128_GCM_SHA256"]
        dfs.append(df)
    data = pd.concat(dfs, ignore_index=True)
    for algo in CLASSIC_ALGOS:
        subset = data[data["Classic Algorithm"] == algo]
        if subset.empty:
            continue
        rows.append({
            "Signing Algorithm": algo,
            "Median Handshake Throughput": subset["Connections in Real Time"].median()
        })
    return pd.DataFrame(rows)

def load_median_handshake_throughput_pq(PQC_KEM):
    rows = []
    for algo in PQ_ALGOS:
        files = glob.glob(str(BASE_FOLDER_PQ / algo / f"tls_handshake_{algo}_run_*.csv"))
        if not files:
            continue
        dfs = []
        for f in files:
            df = pd.read_csv(f)
            df = df[df["Reused Session ID"].isna()]
            df = df[df["KEM Algorithm"] == PQC_KEM]
            dfs.append(df)
        data = pd.concat(dfs, ignore_index=True)
        rows.append({
            "Signing Algorithm": algo,
            "Median Handshake Throughput": data["Connections in Real Time"].median()
        })
    return pd.DataFrame(rows)

# ============================================================
# Plot-Funktion nur leicht angepasst
# ============================================================

def plot_certsize_vs_handshake_throughput():
    # PQ
    df_pq = pd.merge(
        load_cert_sizes_mlkem1024(BASE_FOLDER_STATS_PQ, "MLKEM1024"),
        load_median_handshake_throughput_pq("MLKEM1024"),
        on="Signing Algorithm"
    )
    # Classic
    df_classic = pd.merge(
        load_cert_sizes_classic(BASE_FOLDER_STATS_CLASSIC),
        load_median_handshake_throughput_classic(),
        on="Signing Algorithm"
    )

    plt.figure(figsize=(8, 6))

    # PQ Punkte
    for _, row in df_pq.iterrows():
        plt.scatter(
            row["Cert Size (KB)"],
            row["Median Handshake Throughput"],
            s=80,
            color=PQ_COLOR,
            marker=get_marker(row["Signing Algorithm"]),
            edgecolors="black",
            label=None
        )

    # Classic Punkte
    for _, row in df_classic.iterrows():
        plt.scatter(
            row["Cert Size (KB)"],
            row["Median Handshake Throughput"],
            s=80,
            color=CLASSIC_COLOR,
            marker=get_marker(row["Signing Algorithm"]),
            edgecolors="black",
            label=None
        )

    # Labels
    for _, row in df_pq.iterrows():
        plt.text(row["Cert Size (KB)"]*1.01, row["Median Handshake Throughput"],
                 row["Signing Algorithm"], fontsize=9)
    for _, row in df_classic.iterrows():
        plt.text(row["Cert Size (KB)"]*1.01, row["Median Handshake Throughput"],
                 row["Signing Algorithm"], fontsize=9)

    
    plt.xlabel("Zertifikatsgröße (KB)")
    plt.ylabel("Median TLS-Handshake-Durchsatz\n(Handshakes pro 61 s)")
    plt.title("Zertifikatsgröße vs. TLS-Handshake-Durchsatz\n(ML-KEM-1024)")

    # Legend-Handles
    legend_elements = [
        plt.Line2D([0], [0], marker='o', color='w', label='Classic', markerfacecolor=CLASSIC_COLOR, markersize=10),
        plt.Line2D([0], [0], marker='o', color='w', label='Post-Quantum', markerfacecolor=PQ_COLOR, markersize=10),
        plt.Line2D([0], [0], marker='s', color='k', label='RSA', linestyle='None', markersize=8),
        plt.Line2D([0], [0], marker='o', color='k', label='ECC', linestyle='None', markersize=8),
        plt.Line2D([0], [0], marker='^', color='k', label='Falcon', linestyle='None', markersize=8),
        plt.Line2D([0], [0], marker='D', color='k', label='MLDSA', linestyle='None', markersize=8),
        plt.Line2D([0], [0], marker='X', color='k', label='SPHINCS', linestyle='None', markersize=8)
    ]
    plt.legend(handles=legend_elements, bbox_to_anchor=(1.05, 1), loc='upper left')

    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    SAVE_PATH_SCATTER.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(SAVE_PATH_SCATTER, dpi=300)
    print(f"Plot gespeichert unter: {SAVE_PATH_SCATTER}")

    if matplotlib.get_backend() not in ["Agg","PDF","PS","SVG","Cairo"]:
        plt.show()

def main():
    plot_certsize_vs_handshake_throughput()

if __name__ == "__main__":
    main()
