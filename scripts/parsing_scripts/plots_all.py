import pandas as pd
import glob
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib
from matplotlib import cm

# ============================================================
# PATHS & CONSTANTS
# ============================================================

SCRIPT_DIR = Path(__file__).resolve().parent

SAVE_PATH_SCATTER_SCENARIOS_ALL = Path(
    r"C:\Users\marie\OneDrive\Documents\Fernuni\Masterarbeit\Plots\Alle\PC"
    r"\all_scatter_classic_vs_pq_all_runs.png"
)

SAVE_PATH_SCATTER_SCENARIOS_MEAN = Path(
    r"C:\Users\marie\OneDrive\Documents\Fernuni\Masterarbeit\Plots\Alle\PC"
    r"\all_scatter_MLKEM1024_classic_vs_pq_mean.png"
)

# original data
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
PQ_KEM = "MLKEM1024"

# ============================================================
# Farbpaletten für Classic / PQ
# ============================================================

CLASSIC_CMAP = cm.Blues
PQ_CMAP = cm.Oranges

def make_color_map(algos, cmap, start=0.4, end=0.9):
    """Gibt dict: algorithm -> Farbe zurück"""
    n = len(algos)
    return {
        algo: cmap(start + i * (end - start) / max(n - 1, 1))
        for i, algo in enumerate(sorted(algos))
    }

CLASSIC_COLORS = make_color_map(CLASSIC_ALGOS, CLASSIC_CMAP)
PQ_COLORS = make_color_map(PQ_ALGOS, PQ_CMAP)

def get_algo_color(algo, mode):
    if mode == "classic":
        return CLASSIC_COLORS.get(algo, "blue")
    else:
        return PQ_COLORS.get(algo, "orange")

# ============================================================
# HELPER FUNCTIONS & COLLECT DATA (Handshakes, User Time, Real Time)
# ============================================================

# --- Handshakes in 61s ---
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

# --- Median User Time ---
def collect_classic_median_duration(base_path, scenario_id):
    files = glob.glob(str(base_path / "classic_results_run_*.csv"))
    dfs = []
    for f in files:
        df = pd.read_csv(f)
        df = df[df["Reused Session ID"].isna()]
        df = df[df["Ciphersuite"] == CLASSIC_CS]
        df = df[df["Classic Algorithm"].isin(CLASSIC_ALGOS)]
        df["User Time per Handshake"] = df["User Time (s)"] / df["Connections in User Time"]
        df = df.assign(
            scenario=scenario_id,
            mode="classic",
            algorithm=df["Classic Algorithm"],
            value=df["User Time per Handshake"]
        )
        dfs.append(df[["scenario", "mode", "algorithm", "value"]])
    return pd.concat(dfs, ignore_index=True)

def collect_pq_median_duration(base_path, scenario_id):
    dfs = []
    for algo in PQ_ALGOS:
        files = glob.glob(str(base_path / algo / f"tls_handshake_{algo}_run_*.csv"))
        for f in files:
            df = pd.read_csv(f)
            df = df[df["Reused Session ID"].isna()]
            df = df[df["KEM Algorithm"] == PQ_KEM]
            df["User Time per Handshake"] = df["User Time (s)"] / df["Connections in User Time"]
            df = df.assign(
                scenario=scenario_id,
                mode="pq",
                algorithm=algo,
                value=df["User Time per Handshake"]
            )
            dfs.append(df[["scenario", "mode", "algorithm", "value"]])
    return pd.concat(dfs, ignore_index=True)

def collect_all_median_duration():
    all_dfs = []
    for sc_id, paths in SCENARIOS.items():
        all_dfs.append(collect_classic_median_duration(paths["classic"], sc_id))
        all_dfs.append(collect_pq_median_duration(paths["pq"], sc_id))
    return pd.concat(all_dfs, ignore_index=True) if all_dfs else pd.DataFrame(columns=["scenario","mode","algorithm","value"])

# --- Median Real Time ---
def collect_classic_median_real_time(base_path, scenario_id):
    files = glob.glob(str(base_path / "classic_results_run_*.csv"))
    dfs = []
    for f in files:
        df = pd.read_csv(f)
        df = df[df["Reused Session ID"].isna()]
        df = df[df["Ciphersuite"] == CLASSIC_CS]
        df = df[df["Classic Algorithm"].isin(CLASSIC_ALGOS)]
        df["Real Time per Handshake"] = df["Real Time (s)"] / df["Connections in Real Time"]
        df = df.assign(
            scenario=scenario_id,
            mode="classic",
            algorithm=df["Classic Algorithm"],
            value=df["Real Time per Handshake"]
        )
        dfs.append(df[["scenario","mode","algorithm","value"]])
    return pd.concat(dfs, ignore_index=True)

def collect_pq_median_real_time(base_path, scenario_id):
    dfs = []
    for algo in PQ_ALGOS:
        files = glob.glob(str(base_path / algo / f"tls_handshake_{algo}_run_*.csv"))
        for f in files:
            df = pd.read_csv(f)
            df = df[df["Reused Session ID"].isna()]
            df = df[df["KEM Algorithm"] == PQ_KEM]
            df["Real Time per Handshake"] = df["Real Time (s)"] / df["Connections in Real Time"]
            df = df.assign(
                scenario=scenario_id,
                mode="pq",
                algorithm=algo,
                value=df["Real Time per Handshake"]
            )
            dfs.append(df[["scenario","mode","algorithm","value"]])
    return pd.concat(dfs, ignore_index=True)

def collect_all_median_real_time():
    all_dfs = []
    for sc_id, paths in SCENARIOS.items():
        all_dfs.append(collect_classic_median_real_time(paths["classic"], sc_id))
        all_dfs.append(collect_pq_median_real_time(paths["pq"], sc_id))
    return pd.concat(all_dfs, ignore_index=True) if all_dfs else pd.DataFrame(columns=["scenario","mode","algorithm","value"])

# ============================================================
# PLOTTING FUNCTIONS (Farben eingebaut)
# ============================================================

def plot_scatter_scenarios(show="all"):
    data = collect_all_data()
    if show == "mean":
        data = data.groupby(["scenario","mode","algorithm"], as_index=False).agg(value=("value","mean"))
    x_labels,x_positions,idx = [],{},0
    for sc in [1,2,3]:
        for mode in ["classic","pq"]:
            x_labels.append(f"S{sc} – {mode}")
            x_positions[(sc,mode)] = idx
            idx +=1
    plt.figure(figsize=(12,6))
    algos = data["algorithm"].unique()
    offsets = {a:0.0 for a in algos}
    point_size = 60 if show=="mean" else 25
    alpha = 0.9 if show=="mean" else 0.7
    for algo in algos:
        subset = data[data["algorithm"]==algo]
        xs = [x_positions[(r.scenario,r.mode)]+offsets[algo] for r in subset.itertuples()]
        ys = subset["value"].values
        subset_sorted = subset.sort_values(["scenario","mode"])
        xs_sorted = [x_positions[(r.scenario,r.mode)]+offsets[algo] for r in subset_sorted.itertuples()]
        ys_sorted = subset_sorted["value"].values
        color = get_algo_color(algo, subset.iloc[0]["mode"])
        plt.plot(xs_sorted, ys_sorted, linestyle='-', color=color, alpha=0.6)
        plt.scatter(xs, ys, color=color, label=algo, s=point_size, alpha=alpha)
    title_suffix = "Mittelwert pro Signatur" if show=="mean" else "Alle Runs"
    plt.title(f"TLS-Handshake-Performance: Classic vs PQ über Szenarien ({title_suffix})")
    plt.xticks(range(len(x_labels)), x_labels, rotation=30)
    plt.ylabel("Abgeschlossene TLS-Handshakes in 61 s (Realzeit)")
    plt.legend(bbox_to_anchor=(1.02,1), loc="upper left", title="Signaturalgorithmen")
    plt.text(1.02,0.35,f"Classic: {CLASSIC_CS}\nPQ: {PQ_KEM}", ha="left", va="top", transform=plt.gca().transAxes, fontsize=9, bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8))
    plt.tight_layout()
    save_path = SAVE_PATH_SCATTER_SCENARIOS_MEAN if show=="mean" else SAVE_PATH_SCATTER_SCENARIOS_ALL
    save_path.parent.mkdir(parents=True, exist_ok=True)
    plt.subplots_adjust(right=0.78)  # Achse endet bei 80% der Breite, Legende sitzt rechts daneben

    plt.savefig(save_path, dpi=300)
    print(f"Plot gespeichert unter: {save_path}")
    if matplotlib.get_backend() not in ["Agg","PDF","PS","SVG","Cairo"]:
        plt.show()
    else:
        print("Interaktives Anzeigen unterdrückt.")

def plot_median_duration(show="mean"):
    data = collect_all_median_duration()
    if show=="mean":
        data = data.groupby(["scenario","mode","algorithm"], as_index=False).agg(value=("value","median"))
    x_labels,x_positions,idx = [],{},0
    for sc in [1,2,3]:
        for mode in ["classic","pq"]:
            x_labels.append(f"S{sc} – {mode}")
            x_positions[(sc,mode)] = idx
            idx+=1
    plt.figure(figsize=(12,6))
    algos = data["algorithm"].unique()
    offsets = {a:0.0 for a in algos}
    point_size = 60 if show=="mean" else 25
    alpha = 0.9 if show=="mean" else 0.7
    for algo in algos:
        subset = data[data["algorithm"]==algo]
        xs = [x_positions[(r.scenario,r.mode)]+offsets[algo] for r in subset.itertuples()]
        ys = subset["value"].values
        subset_sorted = subset.sort_values(["scenario","mode"])
        xs_sorted = [x_positions[(r.scenario,r.mode)]+offsets[algo] for r in subset_sorted.itertuples()]
        ys_sorted = subset_sorted["value"].values
        color = get_algo_color(algo, subset.iloc[0]["mode"])
        plt.plot(xs_sorted, ys_sorted, linestyle='-', color=color, alpha=0.6)
        plt.scatter(xs, ys, color=color, label=algo, s=point_size, alpha=alpha)
    plt.title(f"Median User Time pro TLS-Handshake {' (Alle Runs)' if show=='all' else ''}")
    plt.xticks(range(len(x_labels)), x_labels, rotation=30)
    plt.ylabel("Median Dauer pro Handshake (s)")
    plt.legend(bbox_to_anchor=(1.02,1), loc="upper left", title="Signaturalgorithmen")
    plt.text(1.02,0.35,f"Classic: {CLASSIC_CS}\nPQ: {PQ_KEM}", ha="left", va="top", transform=plt.gca().transAxes, fontsize=9, bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8))
    plt.tight_layout()
    save_path = SAVE_PATH_SCATTER_SCENARIOS_MEAN.parent / "all_scatter_median_user_time.png"
    plt.subplots_adjust(right=0.78)  # Achse endet bei 80% der Breite, Legende sitzt rechts daneben

    plt.savefig(save_path, dpi=300)
    print(f"Plot Median User Time gespeichert unter: {save_path}")
    if matplotlib.get_backend() not in ["Agg","PDF","PS","SVG","Cairo"]:
        plt.show()
    else:
        print("Interaktives Anzeigen unterdrückt.")

def plot_median_real_time(show="mean"):
    data = collect_all_median_real_time()
    if show=="mean":
        data = data.groupby(["scenario","mode","algorithm"], as_index=False).agg(value=("value","median"))
    x_labels,x_positions,idx = [],{},0
    for sc in [1,2,3]:
        for mode in ["classic","pq"]:
            x_labels.append(f"S{sc} – {mode}")
            x_positions[(sc,mode)] = idx
            idx+=1
    plt.figure(figsize=(12,6))
    algos = data["algorithm"].unique()
    offsets = {a:0.0 for a in algos}
    point_size = 60 if show=="mean" else 25
    alpha = 0.9 if show=="mean" else 0.7
    for algo in algos:
        subset = data[data["algorithm"]==algo]
        xs = [x_positions[(r.scenario,r.mode)]+offsets[algo] for r in subset.itertuples()]
        ys = subset["value"].values
        subset_sorted = subset.sort_values(["scenario","mode"])
        xs_sorted = [x_positions[(r.scenario,r.mode)]+offsets[algo] for r in subset_sorted.itertuples()]
        ys_sorted = subset_sorted["value"].values
        color = get_algo_color(algo, subset.iloc[0]["mode"])
        plt.plot(xs_sorted, ys_sorted, linestyle='-', color=color, alpha=0.6)
        plt.scatter(xs, ys, color=color, label=algo, s=point_size, alpha=alpha)
    plt.title(f"Median Real Time pro TLS-Handshake {' (Alle Runs)' if show=='all' else ''}")
    plt.xticks(range(len(x_labels)), x_labels, rotation=30)
    plt.ylabel("Median Real Time pro Handshake (s)")
    plt.legend(bbox_to_anchor=(1.02,1), loc="upper left", title="Signaturalgorithmen")
    plt.text(1.02,0.35,f"Classic: {CLASSIC_CS}\nPQ: {PQ_KEM}", ha="left", va="top", transform=plt.gca().transAxes, fontsize=9, bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8))
    plt.tight_layout()
    save_path = SAVE_PATH_SCATTER_SCENARIOS_MEAN.parent / "all_scatter_median_real_time.png"
    plt.subplots_adjust(right=0.78)  # Achse endet bei 80% der Breite, Legende sitzt rechts daneben

    plt.savefig(save_path, dpi=300)
    print(f"Plot Median Real Time gespeichert unter: {save_path}")
    if matplotlib.get_backend() not in ["Agg","PDF","PS","SVG","Cairo"]:
        plt.show()
    else:
        print("Interaktives Anzeigen unterdrückt()")


# ============================================================
# CREATE TABLES WITH MEDIAN AND PERCENTUAL CHANGES
# ============================================================

def make_summary_table(data, value_name, filename_prefix):
    """
    data: DataFrame mit Spalten ['scenario','mode','algorithm','value']
    value_name: z.B. 'Median User Time' oder 'Handshakes'
    filename_prefix: Basisname für CSV-Datei
    """
    
    summary = data.groupby(['scenario','mode','algorithm'], as_index=False)['value'].mean()
    
    # Pivot-Tabelle: Zeilen = Algorithmus, Spalten = Szenario
    pivot = summary.pivot(index='algorithm', columns='scenario', values='value').sort_index()
    
    # Szenario 1 als Baseline
    pivot['Change_S2'] = pivot[2] - pivot[1]
    pivot['Change_S3'] = pivot[3] - pivot[1]
    pivot['Change_S2_%'] = (pivot['Change_S2'] / pivot[1]) * 100
    pivot['Change_S3_%'] = (pivot['Change_S3'] / pivot[1]) * 100
    
    # CSV speichern
    csv_path = SAVE_PATH_SCATTER_SCENARIOS_MEAN.parent / f"{filename_prefix}_summary.csv"
    pivot.to_csv(csv_path, float_format='%.3f')
    print(f"\n[{value_name}] Tabelle gespeichert: {csv_path}\n")
    
    # Tabelle auf Kommandozeile ausgeben
    print(f"--- {value_name} Übersicht ---")
    print(pivot.round(3).to_string())
    print("-"*50)

def create_all_summary_tables():
    # Handshakes in 61s
    data_handshakes = collect_all_data().groupby(['scenario','mode','algorithm'], as_index=False).agg(value=('value','mean'))
    make_summary_table(data_handshakes, "TLS-Handshakes", "handshakes")
    
    # Median User Time
    data_user_time = collect_all_median_duration().groupby(['scenario','mode','algorithm'], as_index=False).agg(value=('value','median'))
    make_summary_table(data_user_time, "Median User Time", "median_user_time")
    
    # Median Real Time
    data_real_time = collect_all_median_real_time().groupby(['scenario','mode','algorithm'], as_index=False).agg(value=('value','median'))
    make_summary_table(data_real_time, "Median Real Time", "median_real_time")


# ============================================================
# MAIN
# ============================================================

def main():
    ## Handshakes in 61s
    plot_scatter_scenarios(show="mean")
    # plot_scatter_scenarios(show="all")

    ## Median User Time
    plot_median_duration(show="mean")

    ## Median Real Time
    plot_median_real_time(show="mean")

    ## Tabellen mit Mittelwerten und Änderungen erstellen
    create_all_summary_tables()

if __name__ == "__main__":
    main()
