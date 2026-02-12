import pandas as pd
import glob
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib

# ============================================================
# CONFIGURATION
# ============================================================

SCENARIO_ID = 1
SCRIPT_DIR = Path(__file__).resolve().parent

BASE_FOLDER = (
    SCRIPT_DIR / ".." / ".." / "test_data" / "results" / "tls_performance"
).resolve()

SAVE_DIR = Path(
    rf"C:\Users\marie\OneDrive\Documents\Fernuni\Masterarbeit\Plots\Szenario_{SCENARIO_ID}_Raspi"
)
SAVE_DIR.mkdir(parents=True, exist_ok=True)

SCENARIOS = {
    1: {
        "Desktop-PC": BASE_FOLDER / "machine_152" / "handshake_results",
        "Raspberry Pi": BASE_FOLDER / "machine_166" / "handshake_results",
    },
}

CLASSIC_CS = "TLS_AES_128_GCM_SHA256"
PQ_KEM = "MLKEM1024"

CLASSIC_ALGOS = [
    "RSA_2048", "RSA_3072", "RSA_4096",
    "prime256v1", "secp384r1", "secp521r1"
]

PQ_ALGOS = [
    "falcon512", "falcon1024",
    "MLDSA44", "MLDSA65", "MLDSA87",
    "sphincssha2128fsimple", "sphincssha2128ssimple"
]

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

ALGO_ORDER = CLASSIC_ALGOS + PQ_ALGOS

# ============================================================
# DATA COLLECTION
# ============================================================

def collect_time(base_path: Path, mode: str, time_col: str, conn_col: str, to_ms=False) -> pd.DataFrame:
    """
    Gibt DataFrame zurück: Algorithm | Platform | Median Time pro Handshake
    """
    rows = []

    if mode == "classic":
        files = glob.glob(str(base_path / "classic" / "classic_results_run_*.csv"))
        for f in files:
            df = pd.read_csv(f)
            df = df[df["Reused Session ID"].isna()]
            df = df[df["Ciphersuite"].str.strip() == CLASSIC_CS]

            for algo in CLASSIC_ALGOS:
                sub = df[df["Classic Algorithm"] == algo]
                if sub.empty:
                    continue
                median_time = (sub[time_col] / sub[conn_col]).median()
                if to_ms:
                    median_time *= 1000
                rows.append({"Algorithm": algo, "Median": median_time})

    elif mode == "pq":
        for algo in PQ_ALGOS:
            files = glob.glob(str(base_path / "pqc" / algo / f"tls_handshake_{algo}_run_*.csv"))
            for f in files:
                df = pd.read_csv(f)
                df = df[df["Reused Session ID"].isna()]
                df = df[df["KEM Algorithm"] == PQ_KEM]
                median_time = (df[time_col] / df[conn_col]).median()
                if to_ms:
                    median_time *= 1000
                rows.append({"Algorithm": algo, "Median": median_time})
    else:
        raise ValueError(mode)

    return pd.DataFrame(rows)

def collect_connections(base_path: Path, mode: str) -> pd.DataFrame:
    """
    Gibt DataFrame zurück: Algorithm | Platform | Connections pro Minute
    """
    rows = []

    if mode == "classic":
        files = glob.glob(str(base_path / "classic" / "classic_results_run_*.csv"))
        for f in files:
            df = pd.read_csv(f)
            df = df[df["Reused Session ID"].isna()]
            df = df[df["Ciphersuite"].str.strip() == CLASSIC_CS]

            for algo in CLASSIC_ALGOS:
                sub = df[df["Classic Algorithm"] == algo]
                if sub.empty:
                    continue
                total_connections = sub["Connections in Real Time"].sum()
                rows.append({"Algorithm": algo, "Connections": total_connections})

    elif mode == "pq":
        for algo in PQ_ALGOS:
            files = glob.glob(str(base_path / "pqc" / algo / f"tls_handshake_{algo}_run_*.csv"))
            for f in files:
                df = pd.read_csv(f)
                df = df[df["Reused Session ID"].isna()]
                df = df[df["KEM Algorithm"] == PQ_KEM]
                total_connections = df["Connections in Real Time"].sum()
                rows.append({"Algorithm": algo, "Connections": total_connections})

    else:
        raise ValueError(mode)

    return pd.DataFrame(rows)

# ============================================================
# AGGREGATION & PLOTTING
# ============================================================

def build_summary_table(time_col: str, conn_col: str, metric_name: str, to_ms=False):
    dfs = []

    for platform_label, path in SCENARIOS[SCENARIO_ID].items():
        df_classic = collect_time(path, "classic", time_col, conn_col, to_ms=to_ms)
        df_classic["Platform"] = platform_label
        df_classic["Mode"] = "Classic"

        df_pq = collect_time(path, "pq", time_col, conn_col, to_ms=to_ms)
        df_pq["Platform"] = platform_label
        df_pq["Mode"] = "Post-Quantum"

        dfs.append(pd.concat([df_classic, df_pq], ignore_index=True))

    df_all = pd.concat(dfs, ignore_index=True)

    # Median über Runs
    df_all_grouped = df_all.groupby(["Algorithm", "Platform"])["Median"].median().reset_index()

    # Pivot für Tabelle
    df_pivot = df_all_grouped.pivot(index="Algorithm", columns="Platform", values="Median").reindex(ALGO_ORDER).reset_index()
    df_pivot.rename(columns={
        "Desktop-PC": f"Desktop {metric_name} ({'ms' if to_ms else 's'})",
        "Raspberry Pi": f"Raspberry Pi {metric_name} ({'ms' if to_ms else 's'})"
    }, inplace=True)

    df_pivot[f"Faktor Pi / Desktop"] = df_pivot[f"Raspberry Pi {metric_name} ({'ms' if to_ms else 's'})"] / df_pivot[f"Desktop {metric_name} ({'ms' if to_ms else 's'})"]

    # Korrekte Namen einfügen
    df_pivot["Algorithm"] = df_pivot["Algorithm"].map(ALGO_MAPPING)

    # CSV speichern
    csv_path = SAVE_DIR / f"scenario{SCENARIO_ID}_{metric_name.lower().replace(' ', '_')}_table.csv"
    df_pivot.to_csv(csv_path, index=False, float_format="%.3f")
    print(f"{metric_name}-Tabelle gespeichert unter: {csv_path}")

    return df_pivot

def build_connections_table():
    dfs = []

    for platform_label, path in SCENARIOS[SCENARIO_ID].items():
        df_classic = collect_connections(path, "classic")
        df_classic["Platform"] = platform_label
        df_classic["Mode"] = "Classic"

        df_pq = collect_connections(path, "pq")
        df_pq["Platform"] = platform_label
        df_pq["Mode"] = "Post-Quantum"

        dfs.append(pd.concat([df_classic, df_pq], ignore_index=True))

    df_all = pd.concat(dfs, ignore_index=True)

    # Aggregieren über Runs: Median Connections pro Algorithmus/Plattform
    df_all_grouped = df_all.groupby(["Algorithm", "Platform"])["Connections"].median().reset_index()

    # Pivot für Tabelle
    df_pivot = df_all_grouped.pivot(index="Algorithm", columns="Platform", values="Connections").reindex(ALGO_ORDER).reset_index()
    df_pivot.rename(columns={
        "Desktop-PC": "Desktop Connections",
        "Raspberry Pi": "Raspberry Pi Connections"
    }, inplace=True)

    df_pivot["Faktor Pi / Desktop"] = df_pivot["Raspberry Pi Connections"] / df_pivot["Desktop Connections"]
    df_pivot["Algorithm"] = df_pivot["Algorithm"].map(ALGO_MAPPING)

    csv_path = SAVE_DIR / f"scenario{SCENARIO_ID}_connections_table.csv"
    df_pivot.to_csv(csv_path, index=False, float_format="%.3f")
    print(f"Connections-Tabelle gespeichert unter: {csv_path}")

    return df_pivot


def plot_bar_per_algorithm(df: pd.DataFrame, metric_name: str, to_ms=False):
    fig, ax = plt.subplots(figsize=(12, 6))

    algos = df["Algorithm"].tolist()
    desktop = df[f"Desktop {metric_name} ({'ms' if to_ms else 's'})"].tolist() if f"Desktop {metric_name} ({'ms' if to_ms else 's'})" in df else df["Desktop Connections"].tolist()
    raspi = df[f"Raspberry Pi {metric_name} ({'ms' if to_ms else 's'})"].tolist() if f"Raspberry Pi {metric_name} ({'ms' if to_ms else 's'})" in df else df["Raspberry Pi Connections"].tolist()

    x = range(len(algos))
    width = 0.35

    ax.bar([i - width/2 for i in x], desktop, width, label="Desktop-PC")
    ax.bar([i + width/2 for i in x], raspi, width, label="Raspberry Pi")

    ax.set_xticks(x)
    ax.set_xticklabels(algos, rotation=30, ha="right")
    ax.set_ylabel(f"{metric_name} ({'ms' if to_ms else 's'})" if 'Time' in metric_name else metric_name)
    ax.set_title(f"{metric_name} pro Algorithmus – Szenario {SCENARIO_ID}")
    ax.grid(axis="y", linestyle=":", alpha=0.6)
    ax.legend()

    plt.tight_layout()
    plt.savefig(SAVE_DIR / f"scenario{SCENARIO_ID}_{metric_name.lower().replace(' ', '_')}.png", dpi=300)
    plt.show()

# ============================================================
# MAIN
# ============================================================

def main():
    # 1. User Time pro Handshake → ms
    df_user_time = build_summary_table("User Time (s)", "Connections in User Time", "User Time", to_ms=True)
    plot_bar_per_algorithm(df_user_time, "User Time", to_ms=True)

    # 2. Real Time pro Handshake → ms
    df_real_time = build_summary_table("Real Time (s)", "Connections in Real Time", "Real Time", to_ms=True)
    plot_bar_per_algorithm(df_real_time, "Real Time", to_ms=True)

    # 3. Connections pro Minute
    df_connections = build_connections_table()
    plot_bar_per_algorithm(df_connections, "Connections", to_ms=False)

if __name__ == "__main__":
    main()
