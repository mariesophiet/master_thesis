import pandas as pd
import glob
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib

# Ordner der Benchmarks in Plot 1 und Plots 2
BASE_FOLDER_PQ = Path(r"..\..\test_data\results\tls_performance\machine_1111\handshake_results\pqc")
BASE_FOLDER_CLASSIC = Path(r"..\..\test_data\results\tls_performance\machine_1111\handshake_results\classic")


###### Für Plot 1 #####
SAVE_PATH_classic = Path(r"C:\Users\marie\OneDrive\Documents\Fernuni\Masterarbeit\Plots\Szenario_1\sc1_plot1_classic.png")
SAVE_PATH_pq = Path(r"C:\Users\marie\OneDrive\Documents\Fernuni\Masterarbeit\Plots\Szenario_1\sc1_plot1_pq.png")

### Plot 1 Classic ###
def plot1_classic():
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

    y_col = "Connections in Real Time"

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

    plt.title(f"Sz1a: TLS-Handshake-Durchsatz ({cs}, klassische Signaturen)")
    plt.suptitle("")
    plt.xlabel("Signaturalgorithmus")
    plt.ylabel("Abgeschlossene TLS-Handshakes in 61 s (Realzeit)")
    plt.xticks(rotation=30)

    # optionale Punkte für einzelne Runs
    for algo in algo_order:
        subset = df_sz1[df_sz1["Classic Algorithm"] == algo]
        plt.scatter(
            [algo]*len(subset),
            subset[y_col],
            alpha=0.6,
            s=20
        )

    plt.tight_layout()

    SAVE_PATH_classic.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(SAVE_PATH_classic, dpi=300)
    print(f"Plot gespeichert unter: {SAVE_PATH_classic}")


### Plot 1 PQC ###
PQ_ALGOS = [
    "falcon512", "falcon1024",
    "MLDSA44", "MLDSA65", "MLDSA87",
    "sphincssha2128fsimple", "sphincssha2128ssimple"
]

def plot1_pqc():
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

    y_col = "Connections in Real Time"

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

    plt.title("TLS-Handshake-Durchsatz (Post-Quantum-Signaturen)")
    plt.suptitle("")
    plt.xlabel("Signaturalgorithmus")
    plt.ylabel("Abgeschlossene TLS-Handshakes in 61 s (Realzeit)")
    plt.xticks(rotation=30)

    for algo in PQ_ALGOS:
        subset = data[data["Signing Algorithm"] == algo]
        plt.scatter(
            [algo]*len(subset),
            subset[y_col],
            alpha=0.6,
            s=20
        )

    plt.tight_layout()
    SAVE_PATH_pq.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(SAVE_PATH_pq, dpi=300)
    print(f"Plot gespeichert unter: {SAVE_PATH_pq}")

    if matplotlib.get_backend() not in ["Agg", "PDF", "PS", "SVG", "Cairo"]:
        plt.show()
    else:
        print("Interaktives Anzeigen des Plots wird übersprungen.")


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

    y_col = "Connections in Real Time"

    data["Signing Algorithm"] = pd.Categorical(
        data["Signing Algorithm"],
        categories=algos,
        ordered=True
    )

    plt.figure(figsize=(10, 5))

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

    for algo in algos:
        subset = data[data["Signing Algorithm"] == algo]
        plt.scatter([algo]*len(subset), subset[y_col], alpha=0.6, s=20)

    plt.tight_layout()
    save_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(save_path, dpi=300)
    print(f"Plot gespeichert unter: {save_path}")

    if matplotlib.get_backend() not in ["Agg", "PDF", "PS", "SVG", "Cairo"]:
        plt.show()
    else:
        print("Interaktives Anzeigen unterdrückt.")


def plot2_dilithium_falcon():
    plot_algo_comparison(DILITHIUM_ALGOS, SAVE_PATH_DILITHIUM, "TLS-Handshake: Dilithium 2 vs 3")
    plot_algo_comparison(FALCON_ALGOS, SAVE_PATH_FALCON, "TLS-Handshake: Falcon 512 vs 1024")


###### Hauptprogramm ######

def main():
    #plot1_classic()
    #plot1_pqc()
    plot2_dilithium_falcon()

if __name__ == "__main__":
    main()
