import pandas as pd
import glob
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib


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

SCRIPT_DIR = Path(__file__).resolve().parent

BASE_FOLDER_CLASSIC = (
    SCRIPT_DIR
    / ".." / ".."
    / "test_data" / "results" / "tls_performance"
    / "machine_1111" / "handshake_results" / "classic"
)

BASE_FOLDER_PQ = (
    SCRIPT_DIR
    / ".." / ".."
    / "test_data" / "results" / "tls_performance"
    / "machine_1111" / "handshake_results" / "pqc"
).resolve()

BASE_FOLDER_STATS = (
    SCRIPT_DIR
    / ".." / ".."
    / "test_data" / "up_results" / "tls_performance"
    / "machine_1_messagesizes_test" / "traffic" / "pqc" / "tls_stats"
).resolve()

BASE_FOLDER_STATS_CLASSIC = (
    SCRIPT_DIR
    / ".." / ".."
    / "test_data" / "up_results" / "tls_performance"
    / "machine_1_messagesizes_test" / "traffic" / "classic" / "tls_stats"
)

def load_cert_sizes_classic(stats_base_folder):
    rows = []

    for algo in CLASSIC_ALGOS:
        pattern = stats_base_folder / f"pcap_*_{algo}_tls_handshake_stats.csv"
        files = glob.glob(str(pattern))

        if not files:
            print(f"[WARN] Keine Stats-Datei für Classic {algo}")
            continue

        df = pd.read_csv(files[0])
        cert_row = df[df["TLS Type"] == "Certificate"]

        if cert_row.empty:
            print(f"[WARN] Keine Certificate-Zeile für Classic {algo}")
            continue

        cert_size_kb = cert_row["Avg Len"].iloc[0] / 1024

        rows.append({
            "Signing Algorithm": algo,
            "Cert Size (KB)": cert_size_kb
        })

    return pd.DataFrame(rows)

def load_cert_sizes_mlkem1024(stats_base_folder, kem):
    rows = []

    for algo in PQ_ALGOS:
        pattern = stats_base_folder / f"pcap_*_{algo}_{kem}_tls_handshake_stats.csv"
        files = glob.glob(str(pattern))

        if not files:
            print(f"[WARN] Keine Stats-Datei für {algo}")
            continue

        df = pd.read_csv(files[0])
        cert_row = df[df["TLS Type"] == "Certificate"]

        if cert_row.empty:
            print(f"[WARN] Keine Certificate-Zeile für {algo}")
            continue

        cert_size_kb = cert_row["Avg Len"].iloc[0] / 1024

        rows.append({
            "Signing Algorithm": algo,
            "Cert Size (KB)": cert_size_kb
        })

    return pd.DataFrame(rows)

def load_median_handshake_throughput_classic():
    rows = []

    files = glob.glob(str(BASE_FOLDER_CLASSIC / "classic_results_run_*.csv"))
    if not files:
        print("[WARN] Keine Classic-Handshakes gefunden")
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

        median_tp = subset["Connections in Real Time"].median()

        rows.append({
            "Signing Algorithm": algo,
            "Median Handshake Throughput": median_tp
        })

    return pd.DataFrame(rows)




def load_median_handshake_throughput_pq(PQC_KEM):
    """
    Berechnet den Median des TLS-Handshake-Durchsatzes
    pro PQ-Signaturalgorithmus (nur MLKEM1024).
    """
    rows = []

    for algo in PQ_ALGOS:
        pattern = BASE_FOLDER_PQ / algo / f"tls_handshake_{algo}_run_*.csv"
        files = glob.glob(str(pattern))

        if not files:
            print(f"[WARN] Keine Handshake-Dateien für {algo}")
            continue

        dfs = []
        for f in files:
            df = pd.read_csv(f)
            df = df[df["Reused Session ID"].isna()]
            df = df[df["KEM Algorithm"] == PQC_KEM]
            dfs.append(df)

        data = pd.concat(dfs, ignore_index=True)

        median_throughput = data["Connections in Real Time"].median()

        rows.append({
            "Signing Algorithm": algo,
            "Median Handshake Throughput": median_throughput
        })

    return pd.DataFrame(rows)

SAVE_PATH_SCATTER = Path(
    r"C:\Users\marie\OneDrive\Documents\Fernuni\Masterarbeit\Plots\Szenario_1"
    r"\sc1_certsize_vs_throughput_mlkem1024.png"
)

def plot_certsize_vs_handshake_throughput():
    # PQ
    cert_sizes_pq = load_cert_sizes_mlkem1024(BASE_FOLDER_STATS, "MLKEM1024")
    medians_pq = load_median_handshake_throughput_pq("MLKEM1024")
    df_pq = pd.merge(cert_sizes_pq, medians_pq, on="Signing Algorithm")

    # Classic
    cert_sizes_classic = load_cert_sizes_classic(BASE_FOLDER_STATS_CLASSIC)
    medians_classic = load_median_handshake_throughput_classic()
    df_classic = pd.merge(cert_sizes_classic, medians_classic, on="Signing Algorithm")

    plt.figure(figsize=(8, 6))

    # PQ Punkte
    plt.scatter(
        df_pq["Cert Size (KB)"],
        df_pq["Median Handshake Throughput"],
        s=70,
        label="Post-Quantum Signaturen",
        alpha=0.8
    )

    # Classic Punkte 
    plt.scatter(
        df_classic["Cert Size (KB)"],
        df_classic["Median Handshake Throughput"],
        s=90,
        marker="s",
        label="Klassische Signaturen",
        alpha=0.8
    )

    # Labels
    for _, row in df_pq.iterrows():
        plt.text(
            row["Cert Size (KB)"] * 1.01,
            row["Median Handshake Throughput"],
            row["Signing Algorithm"],
            fontsize=9
        )

    for _, row in df_classic.iterrows():
        plt.text(
            row["Cert Size (KB)"] * 1.01,
            row["Median Handshake Throughput"],
            row["Signing Algorithm"],
            fontsize=9
        )

    plt.xlabel("Zertifikatsgröße (KB)")
    plt.ylabel("Median TLS-Handshake-Durchsatz\n(Handshakes pro 61 s)")
    plt.title("Zertifikatsgröße vs. TLS-Handshake-Durchsatz\n(ML-KEM-1024)")

    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()

    SAVE_PATH_SCATTER.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(SAVE_PATH_SCATTER, dpi=300)
    print(f"Plot gespeichert unter: {SAVE_PATH_SCATTER}")

    if matplotlib.get_backend() not in ["Agg", "PDF", "PS", "SVG", "Cairo"]:
        plt.show()


def main():
    plot_certsize_vs_handshake_throughput()

if __name__ == "__main__":
    main()