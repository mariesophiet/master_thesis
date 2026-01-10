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
    / "machine_22222" / "handshake_results" / "pqc"
).resolve()

BASE_FOLDER_CLASSIC = (
    SCRIPT_DIR
    / ".." / ".."
    / "test_data" / "results" / "tls_performance"
    / "machine_22222" / "handshake_results" / "classic"
).resolve()

SC = 2

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


### Plot 1 Classic ###
def plot1_classic(metric="connections"):
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

    # Filtern der Metrik
    if metric == "connections":
        y_col = "Connections in Real Time"
        y_label = "Abgeschlossene TLS-Handshakes in 61 s (Realzeit)"
        title_base = "TLS-Handshake-Durchsatz"

    elif metric == "user_time":
        df_sz1 = df_sz1.copy()
        df_sz1["User Time per Handshake"] = (
            df_sz1["User Time (s)"] / df_sz1["Connections in User Time"]
        )
        y_col = "User Time per Handshake"
        y_label = "Median User Time pro TLS-Handshake [s]"
        title_base = "Median User Time pro TLS-Handshake"
    elif metric == "real_time":
        df_sz1 = df_sz1.copy()
        df_sz1["Real Time per Handshake"] = (
            df_sz1["Real Time (s)"] / df_sz1["Connections in Real Time"]
        )
        y_col = "Real Time per Handshake"
        y_label = "Median Real Time pro TLS-Handshake [s]"
        title_base = "Median Real Time pro TLS-Handshake"


    else:
        raise ValueError(f"Unbekannte Metrik: {metric}")

    algo_order = [
        "RSA_2048",
        "RSA_3072",
        "RSA_4096",
        "prime256v1",
        "secp384r1",
        "secp521r1"
    ]

    df_sz1["Classic Algorithm"] = pd.Categorical(
        df_sz1["Classic Algorithm"],
        categories=algo_order,
        ordered=True
    )

    plt.figure(figsize=(10, 5))

    df_sz1.boxplot(
        column=y_col,
        by="Classic Algorithm",
        showfliers=True
    )

    plt.title(f"{title_base} klassisch \n({cs})")    
    plt.suptitle("")
    plt.xlabel("Signaturalgorithmus")
    plt.ylabel(y_label)
    plt.xticks(rotation=30)

    # optionale Punkte für einzelne Runs
    for i, algo in enumerate(algo_order, start=1):
        subset = df_sz1[df_sz1["Classic Algorithm"] == algo]
        plt.scatter(
            [i]*len(subset),
            subset[y_col],
            alpha=0.6,
            s=20
        )

    plt.tight_layout()

    if metric == "connections":
        SAVE_PATH_classic.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(SAVE_PATH_classic, dpi=300)
        print(f"Plot gespeichert unter: {SAVE_PATH_classic}")
    elif metric == "user_time":
        SAVE_PATH_classic_user_time.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(SAVE_PATH_classic_user_time, dpi=300)
        print(f"Plot gespeichert unter: {SAVE_PATH_classic_user_time}")
    elif metric == "real_time":
        SAVE_PATH_classic_real_time.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(SAVE_PATH_classic_real_time, dpi=300)
        print(f"Plot gespeichert unter: {SAVE_PATH_classic_real_time}")


    # speichere das y-Achsen-Limitm, sodass pq mit der gleichen Skala geplottet wird
    y_max = df_sz1[y_col].max()
    y_lim = y_max * 1.05  # 5 % Puffer

    plt.ylim(0, y_lim)
    
    return y_lim



### Plot 1 PQC ###
PQ_ALGOS = [
    "falcon512", "falcon1024",
    "MLDSA44", "MLDSA65", "MLDSA87",
    "sphincssha2128fsimple", "sphincssha2128ssimple"
]

PQC_KEM = "MLKEM1024"

def plot1_pqc(y_lim, metric="connections"):
    """
    Plottet einen Boxplot der TLS-Handshakes für Post-Quantum-Signaturalgorithmen.
    """
    all_files = []
    for algo in PQ_ALGOS:
        pattern = BASE_FOLDER_PQ / algo / f"tls_handshake_{algo}_run_*.csv"
        files = glob.glob(str(pattern))
        all_files.extend(files)
        print(f"{len(files)} Dateien für {algo} gefunden")
    
    if not all_files:
        print("Keine CSV-Dateien gefunden. Prüfe BASE_FOLDER und Unterordner.")
        return

    dfs = []
    for i, f in enumerate(all_files, start=1):
        df = pd.read_csv(f)
        df["run"] = i
        dfs.append(df)

    data = pd.concat(dfs, ignore_index=True)
    data = data[data["Reused Session ID"].isna()]
    data = data[data["KEM Algorithm"] == PQC_KEM]

    # Filtern der Metrik
    if metric == "connections":
        y_col = "Connections in Real Time"
        y_label = "Abgeschlossene TLS-Handshakes in 61 s (Realzeit)"
        title_base = "TLS-Handshake-Durchsatz"

    elif metric == "user_time":
        data = data.copy()
        data["User Time per Handshake"] = (
            data["User Time (s)"] / data["Connections in User Time"]
        )
        y_col = "User Time per Handshake"
        y_label = "Median User Time pro TLS-Handshake [s]"
        title_base = "Median User Time pro TLS-Handshake"
    elif metric == "real_time":
        data = data.copy()
        data["Real Time per Handshake"] = (
            data["Real Time (s)"] / data["Connections in Real Time"]
        )
        y_col = "Real Time per Handshake"
        y_label = "Median Real Time pro TLS-Handshake [s]"
        title_base = "Median Real Time pro TLS-Handshake"


    else:
        raise ValueError(f"Unbekannte Metrik: {metric}")


    data["Signing Algorithm"] = pd.Categorical(
        data["Signing Algorithm"],
        categories=PQ_ALGOS,
        ordered=True
    )

    plt.figure(figsize=(12, 6))

    data.boxplot(
        column=y_col,
        by="Signing Algorithm",
        showfliers=True
    )

    plt.title(f"{title_base} post-quantum ({PQC_KEM})")
    plt.suptitle("")
    plt.xlabel("Signaturalgorithmus")
    plt.ylabel(y_label)
    plt.xticks(rotation=30)
    # ylim soll wie bei klassichem Plot sein
    plt.ylim(0, y_lim)

    for i, algo in enumerate(PQ_ALGOS, start=1):
        subset = data[data["Signing Algorithm"] == algo]
        plt.scatter(
            [i]*len(subset),
            subset[y_col],
            alpha=0.6,
            s=20
        )

    plt.tight_layout()
    if metric == "connections":
        SAVE_PATH_pq.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(SAVE_PATH_pq, dpi=300)
        print(f"Plot gespeichert unter: {SAVE_PATH_pq}")
    elif metric == "user_time":
        SAVE_PATH_pq_user_time.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(SAVE_PATH_pq_user_time, dpi=300)
        print(f"Plot gespeichert unter: {SAVE_PATH_pq_user_time}")
    elif metric == "real_time":
        SAVE_PATH_pq_real_time.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(SAVE_PATH_pq_real_time, dpi=300)
        print(f"Plot gespeichert unter: {SAVE_PATH_pq_real_time}")


    if matplotlib.get_backend() not in ["Agg", "PDF", "PS", "SVG", "Cairo"]:
        plt.show()
    else:
        print("Interaktives Anzeigen des Plots wird übersprungen.")

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
    data = data[data["KEM Algorithm"] == PQC_KEM]

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

######  Plots 2  ######

SAVE_PATH_DILITHIUM = Path(fr"C:\Users\marie\OneDrive\Documents\Fernuni\Masterarbeit\Plots\Szenario_{SC}\sc{SC}_plot2_dilithium.png")
SAVE_PATH_FALCON = Path(fr"C:\Users\marie\OneDrive\Documents\Fernuni\Masterarbeit\Plots\Szenario_{SC}\sc{SC}_plot2_falcon.png")

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
    data = data[data["KEM Algorithm"] == PQC_KEM]

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

    if matplotlib.get_backend() not in ["Agg", "PDF", "PS", "SVG", "Cairo"]:
        plt.show()
    else:
        print("Interaktives Anzeigen unterdrückt.")


def plot2_dilithium_falcon():
    plot_algo_comparison(DILITHIUM_ALGOS, SAVE_PATH_DILITHIUM, f"TLS-Handshake: Dilithium 2 vs 3 ({PQC_KEM})")
    plot_algo_comparison(FALCON_ALGOS, SAVE_PATH_FALCON, f"TLS-Handshake: Falcon 512 vs 1024 ({PQC_KEM})")


###### Hauptprogramm ######

def main():
    # Durchsatz
    y_lim = plot1_classic(metric="connections")
    plot1_pqc(y_lim, metric="connections")
    # User Time pro Handshake
    y_lim = plot1_classic(metric="user_time")
    plot1_pqc(y_lim, metric="user_time")
    # Real Time pro Handshake
    y_lim = plot1_classic(metric="real_time")
    plot1_pqc(y_lim, metric="real_time")
    # Overhead-Faktor Tabellen
    calculate_overhead_classic()
    calculate_overhead_pqc()
    
    # Vergleich der verschiedenen Dilithium und Falcon-Versionen
    #plot2_dilithium_falcon()

if __name__ == "__main__":
    main()
