import pandas as pd
import glob
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib

# ============================================================
# PATHS & CONSTANTS
# ============================================================

SCRIPT_DIR = Path(__file__).resolve().parent

SAVE_PATH_SCATTER_SCENARIOS_ALL = Path(
    r"C:\Users\marie\OneDrive\Documents\Fernuni\Masterarbeit\Plots\Alle"
    r"\scatter_classic_vs_pq_all_runs.png"
)

SAVE_PATH_SCATTER_SCENARIOS_MEAN = Path(
    r"C:\Users\marie\OneDrive\Documents\Fernuni\Masterarbeit\Plots\Alle"
    r"\scatter_classic_vs_pq_mean.png"
)

BASE_FOLDER_PQ = (
    SCRIPT_DIR
    / ".." / ".."
    / "test_data" / "results" / "tls_performance"
).resolve()

BASE_FOLDER_CLASSIC = BASE_FOLDER_PQ

SCENARIOS = {
    1: {
        "classic": BASE_FOLDER_CLASSIC / "machine_1111" / "handshake_results" / "classic",
        "pq": BASE_FOLDER_PQ / "machine_1111" / "handshake_results" / "pqc",
    },
    2: {
        "classic": BASE_FOLDER_CLASSIC / "machine_22222" / "handshake_results" / "classic",
        "pq": BASE_FOLDER_PQ / "machine_22222" / "handshake_results" / "pqc",
    },
    3: {
        "classic": BASE_FOLDER_CLASSIC / "machine_3333" / "handshake_results" / "classic",
        "pq": BASE_FOLDER_PQ / "machine_3333" / "handshake_results" / "pqc",
    },
}

CLASSIC_ALGOS = [
    "RSA_2048", "RSA_3072", "RSA_4096",
    "prime256v1", "secp384r1", "secp521r1"
]

PQ_ALGOS = [
    "falcon512", "falcon1024",
    "MLDSA44", "MLDSA65", "MLDSA87",
    "sphincssha2128fsimple", "sphincssha2128ssimple"
]

CLASSIC_CS = "TLS_AES_128_GCM_SHA256"
PQ_KEM = "MLKEM768"

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def collect_classic_data(base_path, scenario_id):
    files = glob.glob(str(base_path / "classic_results_run_*.csv"))
    dfs = []

    for f in files:
        df = pd.read_csv(f)
        df = df[df["Reused Session ID"].isna()]
        df = df[df["Ciphersuite"] == CLASSIC_CS]
        df = df[df["Classic Algorithm"].isin(CLASSIC_ALGOS)]

        df = df.assign(
            scenario=scenario_id,
            mode="classic",
            algorithm=df["Classic Algorithm"],
            value=df["Connections in Real Time"]
        )

        dfs.append(df[["scenario", "mode", "algorithm", "value"]])

    return pd.concat(dfs, ignore_index=True)


def collect_pq_data(base_path, scenario_id):
    dfs = []

    for algo in PQ_ALGOS:
        files = glob.glob(str(base_path / algo / f"tls_handshake_{algo}_run_*.csv"))

        for f in files:
            df = pd.read_csv(f)
            df = df[df["Reused Session ID"].isna()]
            df = df[df["KEM Algorithm"] == PQ_KEM]

            df = df.assign(
                scenario=scenario_id,
                mode="pq",
                algorithm=algo,
                value=df["Connections in Real Time"]
            )

            dfs.append(df[["scenario", "mode", "algorithm", "value"]])

    return pd.concat(dfs, ignore_index=True)


def collect_all_data():
    all_dfs = []

    for sc_id, paths in SCENARIOS.items():
        all_dfs.append(collect_classic_data(paths["classic"], sc_id))
        all_dfs.append(collect_pq_data(paths["pq"], sc_id))

    return pd.concat(all_dfs, ignore_index=True)

# ============================================================
# PLOT FUNCTION
# ============================================================

def plot_scatter_scenarios(show="all"):
    """
    show = "all"  -> alle Runs als Scatter
    show = "mean" -> Mittelwert pro (Szenario, Mode, Algorithmus)
    """

    if show not in {"all", "mean"}:
        raise ValueError("show must be 'all' or 'mean'")

    data = collect_all_data()

    if show == "mean":
        data = (
            data
            .groupby(["scenario", "mode", "algorithm"], as_index=False)
            .agg(value=("value", "mean"))
        )

    x_labels = []
    x_positions = {}
    idx = 0

    for sc in [1, 2, 3]:
        for mode in ["classic", "pq"]:
            label = f"S{sc} – {mode}"
            x_labels.append(label)
            x_positions[(sc, mode)] = idx
            idx += 1

    plt.figure(figsize=(14, 6))

    algos = data["algorithm"].unique()
    offsets = {a: i * 0.03 for i, a in enumerate(algos)}

    point_size = 60 if show == "mean" else 25
    alpha = 0.9 if show == "mean" else 0.7

    for algo in algos:
        subset = data[data["algorithm"] == algo]

        xs = [
            x_positions[(r.scenario, r.mode)] + offsets[algo]
            for r in subset.itertuples()
        ]

        plt.scatter(
            xs,
            subset["value"],
            label=algo,
            s=point_size,
            alpha=alpha
        )

    title_suffix = "Mittelwert pro Signatur" if show == "mean" else "Alle Runs"

    plt.title(
        f"TLS-Handshake-Performance: Classic vs PQ über Szenarien ({title_suffix})"
    )

    plt.xticks(range(len(x_labels)), x_labels, rotation=30)
    plt.ylabel("Abgeschlossene TLS-Handshakes in 61 s (Realzeit)")
    plt.legend(bbox_to_anchor=(1.02, 1), loc="upper left")
    plt.text(
        1.02, 0.4,  # x>1 verschiebt nach rechts außerhalb der Achse, y=0.4 ist mittig unter legend
        f"Classic: {CLASSIC_CS}\nPQ: {PQ_KEM}",
        ha="left",
        va="top",
        transform=plt.gca().transAxes,
        fontsize=9,
        bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8))
    plt.tight_layout()

    save_path = (
        SAVE_PATH_SCATTER_SCENARIOS_MEAN
        if show == "mean"
        else SAVE_PATH_SCATTER_SCENARIOS_ALL
    )

    save_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(save_path, dpi=300)
    print(f"Plot gespeichert unter: {save_path}")

    if matplotlib.get_backend() not in ["Agg", "PDF", "PS", "SVG", "Cairo"]:
        plt.show()
    else:
        print("Interaktives Anzeigen unterdrückt.")

# ============================================================
# MAIN
# ============================================================

def main():
    plot_scatter_scenarios(show="mean")
    # plot_scatter_scenarios(show="all")

if __name__ == "__main__":
    main()
