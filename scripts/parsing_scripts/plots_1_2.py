import pandas as pd
import glob
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib

# Ordner der Benchmarks in Plot 1 und Plots 2
SCRIPT_DIR = Path(__file__).resolve().parent

BASE_FOLDER_PQ = (
    SCRIPT_DIR
    / ".." / ".."
    / "test_data" / "results" / "tls_performance"
    / "machine_152" / "handshake_results" / "pqc"
).resolve()

BASE_FOLDER_CLASSIC = (
    SCRIPT_DIR
    / ".." / ".."
    / "test_data" / "results" / "tls_performance"
    / "machine_152" / "handshake_results" / "classic"
).resolve()


###### Für Plot 1 #####
SAVE_PATH_classic = Path(r"C:\Users\marie\OneDrive\Documents\Fernuni\Masterarbeit\Plots\Szenario_1\sc1_plot1_classic_connections.png")
SAVE_PATH_pq = Path(r"C:\Users\marie\OneDrive\Documents\Fernuni\Masterarbeit\Plots\Szenario_1\sc1_plot1_pq_connections.png")

SAVE_PATH_classic_user_time = Path(r"C:\Users\marie\OneDrive\Documents\Fernuni\Masterarbeit\Plots\Szenario_1\sc1_plot1_classic_user_time.png")
SAVE_PATH_pq_user_time = Path(r"C:\Users\marie\OneDrive\Documents\Fernuni\Masterarbeit\Plots\Szenario_1\sc1_plot1_pq_user_time.png")

SAVE_PATH_classic_real_time = Path(
    r"C:\Users\marie\OneDrive\Documents\Fernuni\Masterarbeit\Plots\Szenario_1\sc1_plot1_classic_real_time.png"
)
SAVE_PATH_pq_real_time = Path(
    r"C:\Users\marie\OneDrive\Documents\Fernuni\Masterarbeit\Plots\Szenario_1\sc1_plot1_pq_real_time.png"
)

SAVE_PATH_classic_throughput = Path(
    r"C:\Users\marie\OneDrive\Documents\Fernuni\Masterarbeit\Plots\Szenario_1\sc1_plot1_classic_throughput.png"
)
SAVE_PATH_pq_throughput = Path(
    r"C:\Users\marie\OneDrive\Documents\Fernuni\Masterarbeit\Plots\Szenario_1\sc1_plot1_pq_throughput.png"
)



### Plot 1 Classic ###
def plot1_classic(metric="connections", y_lim=None):
    """
    Plottet einen Boxplot der TLS-Handshakes für klassische Signaturalgorithmen.
    """
    files = sorted(glob.glob(str(BASE_FOLDER_CLASSIC / "classic_results_run_*.csv")))
    print(f"{len(files)} Run-Dateien gefunden")

    dfs = []
    for i, f in enumerate(files, start=1):
        df = pd.read_csv(f)
        df["run"] = i
        dfs.append(df)

    data = pd.concat(dfs, ignore_index=True)
    data = data[data["Reused Session ID"].isna()]

    cs = "TLS_AES_128_GCM_SHA256"
    df_sz1 = data[data["Ciphersuite"] == cs].copy()

    # Metrik
    if metric == "connections":
        y_col = "Connections in Real Time"
        y_label = "Abgeschlossene TLS-Handshakes in 61 s (Realzeit)"
        title_base = "TLS-Handshake-Durchsatz"
    elif metric == "user_time":
        df_sz1["User Time per Handshake"] = (df_sz1["User Time (s)"] / df_sz1["Connections in User Time"] * 1000 )
        y_col = "User Time per Handshake"
        y_label = "Median User Time pro TLS-Handshake [ms]"
        title_base = "Median User Time pro TLS-Handshake"
    elif metric == "real_time":
        df_sz1["Real Time per Handshake"] = (df_sz1["Real Time (s)"] / df_sz1["Connections in Real Time"] * 1000)
        y_col = "Real Time per Handshake"
        y_label = "Median Real Time pro TLS-Handshake [ms]"
        title_base = "Median Real Time pro TLS-Handshake"
    elif metric == "throughput":
        df_sz1["Throughput (HS/s)"] = (
            df_sz1["Connections in Real Time"] / df_sz1["Real Time (s)"]
        )
        y_col = "Throughput (HS/s)"
        y_label = "TLS-Handshakes pro Sekunde (Realzeit)"
        title_base = "TLS-Handshake-Durchsatz"

    else:
        raise ValueError(f"Unbekannte Metrik: {metric}")

    # Reihenfolge + lesbare Namen
    ALGO_ORDER_CLASSIC = ["RSA_2048", "RSA_3072", "RSA_4096", "prime256v1", "secp384r1", "secp521r1"]
    ALGO_MAPPING_CLASSIC = {
        "RSA_2048": "RSA-2048",
        "RSA_3072": "RSA-3072",
        "RSA_4096": "RSA-4096",
        "prime256v1": "ECDSA P-256",
        "secp384r1": "ECDSA P-384",
        "secp521r1": "ECDSA P-521"
    }

    df_sz1["Classic Algorithm"] = pd.Categorical(
        df_sz1["Classic Algorithm"],
        categories=ALGO_ORDER_CLASSIC,
        ordered=True
    )

    plt.figure(figsize=(10, 5))
    df_sz1.boxplot(column=y_col, by="Classic Algorithm", showfliers=True)

    plt.title(f"{title_base} klassisch \n({cs})")
    plt.suptitle("")
    plt.xlabel("Signaturalgorithmus")
    plt.ylabel(y_label)
    plt.xticks(ticks=range(1, len(ALGO_ORDER_CLASSIC)+1),
               labels=[ALGO_MAPPING_CLASSIC[a] for a in ALGO_ORDER_CLASSIC],
               rotation=30)

    # Scatterpunkte
    for i, algo in enumerate(ALGO_ORDER_CLASSIC, start=1):
        subset = df_sz1[df_sz1["Classic Algorithm"] == algo]
        plt.scatter([i]*len(subset), subset[y_col], alpha=0.6, s=20)

    plt.tight_layout()

    # speichern
    if metric == "connections":
        SAVE_PATH_classic.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(SAVE_PATH_classic, dpi=300)
    elif metric == "user_time":
        SAVE_PATH_classic_user_time.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(SAVE_PATH_classic_user_time, dpi=300)
    elif metric == "real_time":
        SAVE_PATH_classic_real_time.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(SAVE_PATH_classic_real_time, dpi=300)
    elif metric == "throughput":
        SAVE_PATH_classic_throughput.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(SAVE_PATH_classic_throughput, dpi=300)



    if y_lim is None:
        y_lim = df_sz1[y_col].max() * 1.05

    plt.ylim(0, y_lim)
    return y_lim


PQ_ALGOS = ["falcon512", "falcon1024", "MLDSA44", "MLDSA65", "MLDSA87", "sphincssha2128fsimple", "sphincssha2128ssimple"]
PQ_MAPPING = {
    "falcon512": "Falcon-512",
    "falcon1024": "Falcon-1024",
    "MLDSA44": "ML-DSA-44",
    "MLDSA65": "ML-DSA-65",
    "MLDSA87": "ML-DSA-87",
    "sphincssha2128fsimple": "SPHINCS+SHA2-128f",
    "sphincssha2128ssimple": "SPHINCS+SHA2-128s"
}
PQ_KEM = "MLKEM1024"

### Plot 1 PQC ###
def plot1_pqc(metric="connections", y_lim=None):
    """
    Plottet einen Boxplot der TLS-Handshakes für Post-Quantum-Signaturalgorithmen.
    """

    all_files = []
    for algo in PQ_ALGOS:
        files = glob.glob(str(BASE_FOLDER_PQ / algo / f"tls_handshake_{algo}_run_*.csv"))
        all_files.extend(files)
        print(f"{len(files)} Dateien für {algo} gefunden")

    dfs = []
    for i, f in enumerate(all_files, start=1):
        df = pd.read_csv(f)
        df["run"] = i
        dfs.append(df)

    data = pd.concat(dfs, ignore_index=True)
    data = data[data["Reused Session ID"].isna()]
    data = data[data["KEM Algorithm"] == PQ_KEM]

    # Metrik
    if metric == "connections":
        y_col = "Connections in Real Time"
        y_label = "Abgeschlossene TLS-Handshakes in 61 s (Realzeit)"
        title_base = "TLS-Handshake-Durchsatz"
    elif metric == "user_time":
        data["User Time per Handshake"] = (data["User Time (s)"] / data["Connections in User Time"] * 1000)
        y_col = "User Time per Handshake"
        y_label = "Median User Time pro TLS-Handshake [ms]"
        title_base = "Median User Time pro TLS-Handshake"
    elif metric == "real_time":
        data["Real Time per Handshake"] = (data["Real Time (s)"] / data["Connections in Real Time"] * 1000)
        y_col = "Real Time per Handshake"
        y_label = "Median Real Time pro TLS-Handshake [ms]"
        title_base = "Median Real Time pro TLS-Handshake"
    elif metric == "throughput":
        data["Throughput (HS/s)"] = (
            data["Connections in Real Time"] / data["Real Time (s)"]
        )
        y_col = "Throughput (HS/s)"
        y_label = "TLS-Handshakes pro Sekunde (Realzeit)"
        title_base = "TLS-Handshake-Durchsatz"

    else:
        raise ValueError(f"Unbekannte Metrik: {metric}")

    data["Signing Algorithm"] = pd.Categorical(
        data["Signing Algorithm"],
        categories=PQ_ALGOS,
        ordered=True
    )

    plt.figure(figsize=(12, 6))
    data.boxplot(column=y_col, by="Signing Algorithm", showfliers=True)

    plt.title(f"{title_base} post-quantum ({PQ_KEM})")
    plt.suptitle("")
    plt.xlabel("Signaturalgorithmus")
    plt.ylabel(y_label)
    plt.xticks(ticks=range(1, len(PQ_ALGOS)+1),
               labels=[PQ_MAPPING[a] for a in PQ_ALGOS],
               rotation=30)
    if y_lim is None:
        y_lim = data[y_col].max() * 1.05

    plt.ylim(0, y_lim)


    # Scatterpunkte
    for i, algo in enumerate(PQ_ALGOS, start=1):
        subset = data[data["Signing Algorithm"] == algo]
        plt.scatter([i]*len(subset), subset[y_col], alpha=0.6, s=20)

    plt.tight_layout()

    # speichern
    if metric == "connections":
        SAVE_PATH_pq.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(SAVE_PATH_pq, dpi=300)
    elif metric == "user_time":
        SAVE_PATH_pq_user_time.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(SAVE_PATH_pq_user_time, dpi=300)
    elif metric == "real_time":
        SAVE_PATH_pq_real_time.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(SAVE_PATH_pq_real_time, dpi=300)
    elif metric == "throughput":
        SAVE_PATH_classic_throughput.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(SAVE_PATH_pq_throughput, dpi=300)

    return y_lim

######  Berechne Overhead Faktor = Real Time per HS / User Time per HS  ######

def calculate_overhead_classic():
    """
    Berechnet den Overhead-Faktor (Real Time / User Time) pro Classic Algorithm
    und speichert das Ergebnis als CSV.
    """
    files = sorted(glob.glob(str(BASE_FOLDER_CLASSIC / "classic_results_run_*.csv")))
    dfs = []
    for i, f in enumerate(files, start=1):
        df = pd.read_csv(f)
        df["run"] = i
        dfs.append(df)

    data = pd.concat(dfs, ignore_index=True)
    data = data[data["Reused Session ID"].isna()]
    cs = "TLS_AES_128_GCM_SHA256"
    df_sz1 = data[data["Ciphersuite"] == cs].copy()

    # User Time und Real Time per Handshake
    df_sz1["User Time per Handshake"] = df_sz1["User Time (s)"] / df_sz1["Connections in User Time"]
    df_sz1["Real Time per Handshake"] = df_sz1["Real Time (s)"] / df_sz1["Connections in Real Time"]

    # Overhead-Faktor
    df_sz1["Overhead Factor"] = df_sz1["Real Time per Handshake"] / df_sz1["User Time per Handshake"]

    # Median pro Algorithmus
    overhead_table = (
        df_sz1.groupby("Classic Algorithm", as_index=False)
        .agg(Median_Overhead=("Overhead Factor", "median"))
    )

    # Speichern
    save_path = SAVE_PATH_classic_user_time.parent / "overhead_factor_classic.csv"
    overhead_table.to_csv(save_path, index=False)
    print(f"Overhead-Tabelle Classic gespeichert unter: {save_path}")
    print(overhead_table)
    return overhead_table


def calculate_overhead_pqc():
    """
    Berechnet den Overhead-Faktor (Real Time / User Time) pro PQC Algorithm
    und speichert das Ergebnis als CSV.
    """
    all_files = []
    for algo in PQ_ALGOS:
        files = glob.glob(str(BASE_FOLDER_PQ / algo / f"tls_handshake_{algo}_run_*.csv"))
        all_files.extend(files)
    
    if not all_files:
        print("Keine CSV-Dateien gefunden.")
        return pd.DataFrame()

    dfs = []
    for i, f in enumerate(all_files, start=1):
        df = pd.read_csv(f)
        df["run"] = i
        dfs.append(df)

    data = pd.concat(dfs, ignore_index=True)
    data = data[data["Reused Session ID"].isna()]
    data = data[data["KEM Algorithm"] == PQ_KEM]

    data["User Time per Handshake"] = data["User Time (s)"] / data["Connections in User Time"]
    data["Real Time per Handshake"] = data["Real Time (s)"] / data["Connections in Real Time"]
    data["Overhead Factor"] = data["Real Time per Handshake"] / data["User Time per Handshake"]

    overhead_table = (
        data.groupby("Signing Algorithm", as_index=False)
        .agg(Median_Overhead=("Overhead Factor", "median"))
    )

    save_path = SAVE_PATH_pq_user_time.parent / "overhead_factor_pqc.csv"
    overhead_table.to_csv(save_path, index=False)
    print(f"Overhead-Tabelle PQC gespeichert unter: {save_path}")
    print(overhead_table)
    return overhead_table

######   Tabelle mit 25, 50, 75 Perzentil für Fließtext   ######
def classic_table_with_percentiles():
    files = sorted(glob.glob(str(BASE_FOLDER_CLASSIC / "classic_results_run_*.csv")))
    dfs = [pd.read_csv(f).assign(run=i+1) for i, f in enumerate(files)]
    data = pd.concat(dfs, ignore_index=True)
    data = data[data["Reused Session ID"].isna()]
    cs = "TLS_AES_128_GCM_SHA256"
    df_cs = data[data["Ciphersuite"] == cs].copy()

    df_cs["User Time per HS"] = df_cs["User Time (s)"] / df_cs["Connections in User Time"]
    df_cs["Real Time per HS"] = df_cs["Real Time (s)"] / df_cs["Connections in Real Time"]
    df_cs["Overhead"] = df_cs["Real Time per HS"] / df_cs["User Time per HS"]
    df_cs["Throughput"] = df_cs["Connections in Real Time"] / df_cs["Real Time (s)"]


    table = df_cs.groupby("Classic Algorithm").agg(
        Connections_25th=("Connections in Real Time", lambda x: x.quantile(0.25)),
        Connections_50th=("Connections in Real Time", "median"),
        Connections_75th=("Connections in Real Time", lambda x: x.quantile(0.75)),
        UserTime_25th=("User Time per HS", lambda x: x.quantile(0.25)),
        UserTime_50th=("User Time per HS", "median"),
        UserTime_75th=("User Time per HS", lambda x: x.quantile(0.75)),
        RealTime_25th=("Real Time per HS", lambda x: x.quantile(0.25)),
        RealTime_50th=("Real Time per HS", "median"),
        RealTime_75th=("Real Time per HS", lambda x: x.quantile(0.75)),
        Throughput_25th=("Throughput", lambda x: x.quantile(0.25)),
        Throughput_50th=("Throughput", "median"),
        Throughput_75th=("Throughput", lambda x: x.quantile(0.75)),
        Overhead_25th=("Overhead", lambda x: x.quantile(0.25)),
        Overhead_50th=("Overhead", "median"),
        Overhead_75th=("Overhead", lambda x: x.quantile(0.75))
    ).reset_index()


    save_path = SAVE_PATH_classic_user_time.parent / "classic_table_percentiles.csv"
    table.to_csv(save_path, index=False)
    print(f"Classic-Tabelle mit Perzentilen gespeichert unter: {save_path}")
    return table

def pqc_table_with_percentiles():
    all_files = []
    for algo in PQ_ALGOS:
        files = glob.glob(str(BASE_FOLDER_PQ / algo / f"tls_handshake_{algo}_run_*.csv"))
        all_files.extend(files)
    dfs = [pd.read_csv(f).assign(run=i+1) for i, f in enumerate(all_files)]
    data = pd.concat(dfs, ignore_index=True)
    data = data[data["Reused Session ID"].isna() & (data["KEM Algorithm"] == PQ_KEM)].copy()

    data["User Time per HS"] = data["User Time (s)"] / data["Connections in User Time"]
    data["Real Time per HS"] = data["Real Time (s)"] / data["Connections in Real Time"]
    data["Overhead"] = data["Real Time per HS"] / data["User Time per HS"]

    data["Throughput"] = data["Connections in Real Time"] / data["Real Time (s)"]

    table = data.groupby("Signing Algorithm").agg(
        Connections_25th=("Connections in Real Time", lambda x: x.quantile(0.25)),
        Connections_50th=("Connections in Real Time", "median"),
        Connections_75th=("Connections in Real Time", lambda x: x.quantile(0.75)),
        UserTime_25th=("User Time per HS", lambda x: x.quantile(0.25)),
        UserTime_50th=("User Time per HS", "median"),
        UserTime_75th=("User Time per HS", lambda x: x.quantile(0.75)),
        RealTime_25th=("Real Time per HS", lambda x: x.quantile(0.25)),
        RealTime_50th=("Real Time per HS", "median"),
        RealTime_75th=("Real Time per HS", lambda x: x.quantile(0.75)),
        Throughput_25th=("Throughput", lambda x: x.quantile(0.25)),
        Throughput_50th=("Throughput", "median"),
        Throughput_75th=("Throughput", lambda x: x.quantile(0.75)),
        Overhead_25th=("Overhead", lambda x: x.quantile(0.25)),
        Overhead_50th=("Overhead", "median"),
        Overhead_75th=("Overhead", lambda x: x.quantile(0.75))
    ).reset_index()


    save_path = SAVE_PATH_pq_user_time.parent / "pqc_table_percentiles.csv"
    table.to_csv(save_path, index=False)
    print(f"PQC-Tabelle mit Perzentilen gespeichert unter: {save_path}")
    return table


######  Plots 2  ######

SAVE_PATH_DILITHIUM = Path(r"C:\Users\marie\OneDrive\Documents\Fernuni\Masterarbeit\Plots\Szenario_1\sc1_plot2_dilithium.png")
SAVE_PATH_FALCON = Path(r"C:\Users\marie\OneDrive\Documents\Fernuni\Masterarbeit\Plots\Szenario_1\sc1_plot2_falcon.png")

DILITHIUM_ALGOS = ["MLDSA44", "MLDSA65"]
FALCON_ALGOS = ["falcon512", "falcon1024"]


def plot_algo_comparison(algos, save_path, title):
    """
    Erstellt einen Boxplot zum Vergleich ausgewählter Post-Quantum-Signaturalgorithmen.
    """
    all_files = []
    for algo in algos:
        pattern = BASE_FOLDER_PQ / algo / f"tls_handshake_{algo}_run_*.csv"
        files = glob.glob(str(pattern))
        all_files.extend(files)
        print(f"{len(files)} Dateien für {algo} gefunden")
    
    if not all_files:
        print("Keine CSV-Dateien gefunden.")
        return

    dfs = []
    for i, f in enumerate(all_files, start=1):
        df = pd.read_csv(f)
        df["run"] = i
        dfs.append(df)

    data = pd.concat(dfs, ignore_index=True)
    data = data[data["Reused Session ID"].isna()]
    data = data[data["KEM Algorithm"] == PQ_KEM]

    y_col = "Connections in Real Time"

    data["Signing Algorithm"] = pd.Categorical(
        data["Signing Algorithm"],
        categories=algos,
        ordered=True
    )

    plt.figure(figsize=(12, 6))

    data.boxplot(
        column=y_col,
        by="Signing Algorithm",
        showfliers=True
    )

    plt.title(title)  
    plt.suptitle("")
    plt.xlabel("Signaturalgorithmus")
    plt.ylabel("Abgeschlossene TLS-Handshakes in 61 s (Realzeit)")
    plt.xticks(rotation=30)

    for i, algo in enumerate(algos, start=1):
        subset = data[data["Signing Algorithm"] == algo]
        plt.scatter([i]*len(subset), subset[y_col], alpha=0.6, s=20)

    plt.tight_layout()
    save_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(save_path, dpi=300)
    print(f"Plot gespeichert unter: {save_path}")


def plot2_dilithium_falcon():
    plot_algo_comparison(DILITHIUM_ALGOS, SAVE_PATH_DILITHIUM, f"TLS-Handshake: Dilithium 2 vs 3 ({PQ_KEM})")
    plot_algo_comparison(FALCON_ALGOS, SAVE_PATH_FALCON, f"TLS-Handshake: Falcon 512 vs 1024 ({PQ_KEM})")


###### Hauptprogramm ######

def main():

    # Durchsatz
    y_lim = plot1_classic(metric="connections")
    plot1_pqc(metric="connections", y_lim=y_lim)
    
    # User Time pro Handshake
    y_lim = plot1_classic(metric="user_time")
    plot1_pqc(metric="user_time", y_lim=y_lim)

    # Real Time pro Handshake
    y_lim = plot1_pqc(metric="real_time")          # PQ bestimmt die Skala
    plot1_classic(metric="real_time", y_lim=y_lim) # Classic übernimmt sie

    # Durchsatz pro Sekunde (Realzeit)
    y_lim = plot1_classic(metric="throughput")
    plot1_pqc(metric="throughput", y_lim=y_lim)


    # Overhead-Faktor Tabellen
    calculate_overhead_classic()
    calculate_overhead_pqc()
    classic_table_with_percentiles()
    pqc_table_with_percentiles()


    # Vergleich der verschiedenen Dilithium und Falcon-Versionen
    #plot2_dilithium_falcon()

if __name__ == "__main__":
    main()
