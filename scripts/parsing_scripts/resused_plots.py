import pandas as pd
import glob
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib

# ============================================================
# Pfade
# ============================================================

SCRIPT_DIR = Path(__file__).resolve().parent

BASE_FOLDER_CLASSIC = (
    SCRIPT_DIR
    / ".." / ".."
    / "test_data" / "results" / "tls_performance"
    / "machine_152" / "handshake_results" / "classic"
).resolve()

BASE_FOLDER_PQ = (
    SCRIPT_DIR
    / ".." / ".."
    / "test_data" / "results" / "tls_performance"
    / "machine_152" / "handshake_results" / "pqc"
).resolve()

# ============================================================
# Konfiguration
# ============================================================

PQC_KEM = "MLKEM1024"

METRIC_COL = "Connections in Real Time"
YLABEL = "Relative Änderung des Durchsatzes in % \n(Reused vs. Full Handshake)"

PLOTS_DIR = SCRIPT_DIR / ".." / ".." / "plots" / "scenario_1"
PLOTS_DIR.mkdir(parents=True, exist_ok=True)

SAVE_PATH = PLOTS_DIR / f"sc1_reused_vs_nonreused_relative_change_{PQC_KEM}_horiz.png"

# Classic Reihenfolge
CLASSIC_ORDER = [
    "RSA_2048",
    "RSA_3072",
    "RSA_4096",
    "prime256v1",
    "secp384r1",
    "secp521r1"
]

# PQC Reihenfolge
PQC_ALGOS = [
    "falcon512", "falcon1024",
    "MLDSA44", "MLDSA65", "MLDSA87",
    "sphincssha2128fsimple", "sphincssha2128ssimple"
]

# Abkürzungen nur für SPHINCS
PQC_ABBR = {
    "sphincssha2128fsimple": "SPHINCS+-128f",
    "sphincssha2128ssimple": "SPHINCS+-128s"
}

# ============================================================
# Helper: relative Änderung berechnen
# ============================================================

def relative_change(reused, full):
    return (reused - full) / full * 100.0

# ============================================================
# Classic
# ============================================================

def load_classic_relative():
    files = sorted(glob.glob(str(BASE_FOLDER_CLASSIC / "classic_results_run_*.csv")))
    dfs = []

    for f in files:
        df = pd.read_csv(f)
        dfs.append(df)

    data = pd.concat(dfs, ignore_index=True)
    data = data[data["Ciphersuite"] == "TLS_AES_128_GCM_SHA256"]

    rows = []
    for algo in CLASSIC_ORDER:
        subset = data[data["Classic Algorithm"] == algo]

        if subset.empty:
            continue

        full = subset[subset["Reused Session ID"].isna()][METRIC_COL].median()
        reused = subset[subset["Reused Session ID"] == "*"][METRIC_COL].median()

        if pd.notna(full) and pd.notna(reused):
            rows.append({
                "Algorithm": algo,
                "Relative Change (%)": relative_change(reused, full),
                "Type": "Classic"
            })

    return pd.DataFrame(rows)

# ============================================================
# PQC
# ============================================================

def load_pqc_relative():
    rows = []

    algo_dirs = [p for p in BASE_FOLDER_PQ.iterdir() if p.is_dir()]

    for algo_dir in algo_dirs:
        algo = algo_dir.name
        if algo not in PQC_ALGOS:
            continue
        files = glob.glob(str(algo_dir / f"tls_handshake_{algo}_run_*.csv"))
        if not files:
            continue

        dfs = []
        for f in files:
            df = pd.read_csv(f)
            dfs.append(df)

        data = pd.concat(dfs, ignore_index=True)
        data = data[data["KEM Algorithm"] == PQC_KEM]

        full = data[data["Reused Session ID"].isna()][METRIC_COL].median()
        reused = data[data["Reused Session ID"] == "*"][METRIC_COL].median()

        if pd.notna(full) and pd.notna(reused):
            # Namen anpassen: nur SPHINCS abkürzen, alles andere bleibt
            display_name = PQC_ABBR.get(algo, algo)
            rows.append({
                "Algorithm": display_name,
                "Relative Change (%)": relative_change(reused, full),
                "Type": "PQC"
            })

    return pd.DataFrame(rows)

# ============================================================
# Plot horizontal
# ============================================================

def plot_relative_changes_horiz():
    df_classic = load_classic_relative()
    df_pqc = load_pqc_relative()

    df = pd.concat([df_classic, df_pqc], ignore_index=True)

    # Sortieren nach Classic + PQC Reihenfolge
    algo_order = CLASSIC_ORDER + [PQC_ABBR.get(a, a) for a in PQC_ALGOS]
    df["Algorithm"] = pd.Categorical(df["Algorithm"], categories=algo_order, ordered=True)
    df = df.sort_values("Algorithm")

    plt.figure(figsize=(8, 6))

    colors = df["Type"].map({
        "Classic": "#1f77b4",
        "PQC": "#d62728"
    })

    plt.barh(df["Algorithm"], df["Relative Change (%)"], color=colors)
    plt.axvline(0, color="black", linewidth=0.8)
    plt.xlabel(YLABEL)
    plt.ylabel("Signaturalgorithmus")
    plt.title("Szenario 1: Einfluss von Session Resumption auf TLS-Handshake-Durchsatz")

    plt.tight_layout()
    plt.savefig(SAVE_PATH, dpi=300)
    print(f"Plot gespeichert unter: {SAVE_PATH}")

    if matplotlib.get_backend() not in ["Agg", "PDF", "PS", "SVG", "Cairo"]:
        plt.show()

# ============================================================
# Main
# ============================================================

def main():
    plot_relative_changes_horiz()

if __name__ == "__main__":
    main()
