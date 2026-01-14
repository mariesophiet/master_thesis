import pandas as pd
import glob
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib

# ============================================================
# Pfade – wie bisher
# ============================================================

SCRIPT_DIR = Path(__file__).resolve().parent

BASE_FOLDER_CLASSIC = (
    SCRIPT_DIR / ".." / ".." / "test_data" / "results" / "tls_performance"
    / "machine_166" / "handshake_results" / "classic"
).resolve()

BASE_FOLDER_PQ = (
    SCRIPT_DIR / ".." / ".." / "test_data" / "results" / "tls_performance"
    / "machine_166" / "handshake_results" / "pqc"
).resolve()

scenario = "1"
PQC_KEM = "MLKEM1024"

PLOTS_DIR = SCRIPT_DIR / ".." / ".." / "plots" / "scenario_1_raspi"
PLOTS_DIR.mkdir(parents=True, exist_ok=True)

CSV_PATH = PLOTS_DIR / f"reused_vs_nonreused_values_{PQC_KEM}.csv"

# ============================================================
# Algorithmen
# ============================================================

CLASSIC_ALGOS = [
    "RSA_2048", "RSA_3072", "RSA_4096",
    "prime256v1", "secp384r1", "secp521r1"
]

PQ_ALGOS = [
    "falcon512", "falcon1024",
    "MLDSA44", "MLDSA65", "MLDSA87",
    "SPHINCS+-128f", "SPHINCS+-128s"
]

# ============================================================
# Lade Daten und berechne relative Änderungen
# ============================================================

def compute_relative(df, metric_col, is_pqc=False):
    rows = []
    if is_pqc:
        algo_dirs = [p for p in BASE_FOLDER_PQ.iterdir() if p.is_dir()]
        for algo_dir in algo_dirs:
            algo = algo_dir.name
            if algo not in PQ_ALGOS:
                continue
            files = glob.glob(str(algo_dir / f"tls_handshake_{algo}_run_*.csv"))
            if not files:
                continue
            dfs = [pd.read_csv(f) for f in files]
            data = pd.concat(dfs, ignore_index=True)
            data = data[data["KEM Algorithm"] == PQC_KEM]

            # pro Handshake bei User Time und Real Time
            if metric_col in ["User Time per Handshake", "Real Time per Handshake"]:
                col_base = "User Time (s)" if metric_col == "User Time per Handshake" else "Real Time (s)"
                data[metric_col] = data[col_base] / data["Connections in User Time" if metric_col == "User Time per Handshake" else "Connections in Real Time"]

            full = data[data["Reused Session ID"].isna()][metric_col].median()
            reused = data[data["Reused Session ID"] == "*"][metric_col].median()
            if pd.notna(full) and pd.notna(reused):
                rows.append({"Algorithm": algo, "Type": "PQC",
                             "Full": full, "Reused": reused,
                             "Relative Change (%)": (reused - full)/full*100})
    else:
        files = sorted(glob.glob(str(BASE_FOLDER_CLASSIC / "classic_results_run_*.csv")))
        dfs = [pd.read_csv(f) for f in files]
        data = pd.concat(dfs, ignore_index=True)
        data = data[data["Ciphersuite"] == "TLS_AES_128_GCM_SHA256"]

        if metric_col in ["User Time per Handshake", "Real Time per Handshake"]:
            col_base = "User Time (s)" if metric_col == "User Time per Handshake" else "Real Time (s)"
            data[metric_col] = data[col_base] / data["Connections in User Time" if metric_col == "User Time per Handshake" else "Connections in Real Time"]

        for algo in CLASSIC_ALGOS:
            subset = data[data["Classic Algorithm"] == algo]
            full = subset[subset["Reused Session ID"].isna()][metric_col].median()
            reused = subset[subset["Reused Session ID"] == "*"][metric_col].median()
            if pd.notna(full) and pd.notna(reused):
                rows.append({"Algorithm": algo, "Type": "Classic",
                             "Full": full, "Reused": reused,
                             "Relative Change (%)": (reused - full)/full*100})
    return pd.DataFrame(rows)

# ============================================================
# Plotfunktion für horizontale Balken
# ============================================================

def plot_horizontal(df, metric, filename, xlabel):
    df = df.sort_values(by="Type")  # optional sortieren
    colors = df["Type"].map({"Classic": "#1f77b4", "PQC": "#d62728"})
    plt.figure(figsize=(10, 6))
    plt.barh(df["Algorithm"], df["Relative Change (%)"], color=colors)
    plt.axvline(0, color="black", linewidth=0.8)
    plt.xlabel(xlabel)
    plt.ylabel("Signaturalgorithmus")
    if metric == "Connections":
        title = f"Szenario {scenario}: Relative Änderung (Durchsatz)"
    else:
        title = f"Szenario {scenario}: Relative Änderung ({metric})"
    plt.title(title)
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / filename, dpi=300)
    print(f"Plot gespeichert unter: {PLOTS_DIR / filename}")
    plt.close()

# ============================================================
# Main
# ============================================================

def main():
    # Connections / Durchsatz
    df_classic_conn = compute_relative(None, "Connections in Real Time", is_pqc=False)
    df_classic_conn["Metric"] = "Durchsatz"
    df_pqc_conn     = compute_relative(None, "Connections in Real Time", is_pqc=True)
    df_pqc_conn["Metric"] = "Durchsatz"
    df_conn = pd.concat([df_classic_conn, df_pqc_conn], ignore_index=True)
    plot_horizontal(df_conn, "Durchsatz", "relative_change_connections.png",
                    "Relative Änderung des Durchsatzes (%)")

    # User Time pro Handshake
    df_classic_user = compute_relative(None, "User Time per Handshake", is_pqc=False)
    df_classic_user["Metric"] = "User Time"
    df_pqc_user     = compute_relative(None, "User Time per Handshake", is_pqc=True)
    df_pqc_user["Metric"] = "User Time"
    df_user = pd.concat([df_classic_user, df_pqc_user], ignore_index=True)
    plot_horizontal(df_user, "User Time", "relative_change_user_time.png",
                    "Relative Änderung der User Time pro Handshake (%)")

    # Real Time pro Handshake
    df_classic_real = compute_relative(None, "Real Time per Handshake", is_pqc=False)
    df_classic_real["Metric"] = "Real Time"
    df_pqc_real     = compute_relative(None, "Real Time per Handshake", is_pqc=True)
    df_pqc_real["Metric"] = "Real Time"
    df_real = pd.concat([df_classic_real, df_pqc_real], ignore_index=True)
    plot_horizontal(df_real, "Real Time", "relative_change_real_time.png",
                    "Relative Änderung der Real Time pro Handshake (%)")

    # CSV zusammenführen
    df_all = pd.concat([df_conn, df_user, df_real], ignore_index=True)
    df_all.to_csv(CSV_PATH, index=False)
    print(f"CSV gespeichert unter: {CSV_PATH}")

if __name__ == "__main__":
    main()
