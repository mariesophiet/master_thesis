import pandas as pd
import glob
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np

# ============================================================
# CONFIGURATION
# ============================================================

SCENARIO_ID = 1

SCRIPT_DIR = Path(__file__).resolve().parent
BASE_FOLDER = (SCRIPT_DIR / ".." / ".." / "test_data" / "results" / "tls_performance").resolve()
SAVE_DIR = Path(rf"C:\Users\marie\OneDrive\Documents\Fernuni\Masterarbeit\Plots\Szenario_{SCENARIO_ID}_network")
SAVE_DIR.mkdir(parents=True, exist_ok=True)

# Plattformen
SCENARIOS = {
    1: {
        "Localhost": BASE_FOLDER / "machine_152" / "handshake_results",
        "Netzwerk": BASE_FOLDER / "machine_1_network" / "handshake_results",
    },
}

# Algorithmen intern
CLASSIC_ALGOS = ["RSA_2048", "RSA_3072", "RSA_4096", "prime256v1", "secp384r1", "secp521r1"]
PQ_ALGOS = ["falcon512", "falcon1024", "MLDSA44", "MLDSA65", "MLDSA87", "sphincssha2128fsimple", "sphincssha2128ssimple"]

# Mapping interne Namen → Plotnamen
ALGO_MAPPING = {
    "RSA_2048": "RSA-2048",
    "RSA_3072": "RSA-3072",
    "RSA_4096": "RSA-4096",
    "prime256v1": "ECDSA P-256",
    "secp384r1": "ECDSA P-384",
    "secp521r1": "ECDSA P-521",
    "falcon512": "Falcon-512",
    "falcon1024": "Falcon-1024",
    "MLDSA44": "ML-DSA-44",
    "MLDSA65": "ML-DSA-65",
    "MLDSA87": "ML-DSA-87",
    "sphincssha2128fsimple": "SPHINCS+SHA2-128f",
    "sphincssha2128ssimple": "SPHINCS+SHA2-128s",
}

# Reihenfolge für den Plot: Klassisch klein→groß, dann PQ klein→groß
ALGO_ORDER = [
    "RSA_2048", "RSA_3072", "RSA_4096",
    "prime256v1", "secp384r1", "secp521r1",
    "falcon512", "falcon1024",
    "MLDSA44", "MLDSA65", "MLDSA87",
    "sphincssha2128fsimple", "sphincssha2128ssimple"
]

CLASSIC_CS = "TLS_AES_128_GCM_SHA256"
PQ_KEM = "MLKEM1024"

# ============================================================
# DATA COLLECTION
# ============================================================

def collect_handshake_data(base_path: Path, mode: str) -> pd.DataFrame:
    rows = []

    if mode == "classic":
        files = glob.glob(str(base_path / "classic" / "classic_results_run_*.csv"))
        for f in files:
            df = pd.read_csv(f)
            df = df[df["Reused Session ID"].isna()]
            df = df[df["Ciphersuite"] == CLASSIC_CS]
            for algo in CLASSIC_ALGOS:
                sub = df[df["Classic Algorithm"] == algo]
                if sub.empty:
                    continue
                rows.append({
                    "Algorithm": algo,
                    "Connections": sub["Connections in Real Time"].median(),
                    "UserTime": (sub["User Time (s)"] / sub["Connections in User Time"]).median(),
                    "RealTime": (sub["Real Time (s)"] / sub["Connections in Real Time"]).median()
                })
    elif mode == "pq":
        for algo in PQ_ALGOS:
            files = glob.glob(str(base_path / "pqc" / algo / f"tls_handshake_{algo}_run_*.csv"))
            for f in files:
                df = pd.read_csv(f)
                df = df[df["Reused Session ID"].isna()]
                df = df[df["KEM Algorithm"] == PQ_KEM]
                rows.append({
                    "Algorithm": algo,
                    "Connections": df["Connections in Real Time"].median(),
                    "UserTime": (df["User Time (s)"] / df["Connections in User Time"]).median(),
                    "RealTime": (df["Real Time (s)"] / df["Connections in Real Time"]).median()
                })
    else:
        raise ValueError(mode)

    return pd.DataFrame(rows)

def build_summary_per_algorithm(metric: str) -> pd.DataFrame:
    rows = []
    for platform_label, base_path in SCENARIOS[SCENARIO_ID].items():
        for mode in ["classic", "pq"]:
            df = collect_handshake_data(base_path, mode)
            for _, row in df.iterrows():
                rows.append({
                    "Algorithm": row["Algorithm"],
                    "Platform": platform_label,
                    "Mode": "Classic" if mode == "classic" else "Post-Quantum",
                    "Median": row[metric]
                })
    return pd.DataFrame(rows)

# ============================================================
# PLOTTING
# ============================================================

def plot_metrics_per_algorithm(df_summary: pd.DataFrame, metric_name: str, filename: str):
    algos = [ALGO_MAPPING[a] for a in ALGO_ORDER]
    y_pos = np.arange(len(algos))[::-1]  
    height = 0.35

    localhost_vals = [df_summary[(df_summary['Algorithm']==k) & (df_summary['Platform']=="Localhost")]['Median'].iloc[0] for k in ALGO_ORDER]
    netzwerk_vals = [df_summary[(df_summary['Algorithm']==k) & (df_summary['Platform']=="Netzwerk")]['Median'].iloc[0] for k in ALGO_ORDER]

    fig, ax = plt.subplots(figsize=(10, len(algos)*0.5 + 1))
    ax.barh(y_pos - height/2, localhost_vals, height, label='Localhost', color="#1f77b4")
    ax.barh(y_pos + height/2, netzwerk_vals, height, label='Netzwerk', color="#ff7f0e")

    ax.set_yticks(y_pos)
    ax.set_yticklabels(algos)
    ax.set_xlabel(metric_name)
    ax.set_title(f"{metric_name} pro Algorithmus – Szenario {SCENARIO_ID}")
    ax.grid(axis='x', linestyle=':', alpha=0.6)
    ax.legend()
    plt.tight_layout()
    plt.savefig(SAVE_DIR / filename, dpi=300)
    plt.show()

# ============================================================
# TABLE EXPORT
# ============================================================

def build_network_comparison_table(metric: str) -> pd.DataFrame:
    df_summary = build_summary_per_algorithm(metric)
    rows = []

    for algo in ALGO_ORDER:
        localhost_val = df_summary[(df_summary['Algorithm']==algo) & (df_summary['Platform']=="Localhost")]['Median'].iloc[0]
        netzwerk_val = df_summary[(df_summary['Algorithm']==algo) & (df_summary['Platform']=="Netzwerk")]['Median'].iloc[0]
        factor = netzwerk_val / localhost_val if localhost_val != 0 else np.nan

        rows.append({
            "Algorithm": ALGO_MAPPING[algo],
            "Localhost": localhost_val,
            "Netzwerk": netzwerk_val,
            "Faktor Netzwerk/Localhost": factor
        })

    df_table = pd.DataFrame(rows)
    csv_path = SAVE_DIR / f"scenario{SCENARIO_ID}_network_comparison_{metric}.csv"
    df_table.to_csv(csv_path, index=False, float_format="%.3f")
    print(f"Tabelle für {metric} gespeichert unter: {csv_path}")
    return df_table

# ============================================================
# MAIN
# ============================================================

def main():
    for metric, display_name, file_name in [
        ("Connections", "TLS-Handshakes pro Minute", "connections_per_algo.png"),
        ("UserTime", "Median User Time pro Handshake (s)", "user_time_per_algo.png"),
        ("RealTime", "Median Real Time pro Handshake (s)", "real_time_per_algo.png"),
    ]:
        df_metric = build_summary_per_algorithm(metric)
        plot_metrics_per_algorithm(df_metric, display_name, file_name)
        build_network_comparison_table(metric)

if __name__ == "__main__":
    main()
