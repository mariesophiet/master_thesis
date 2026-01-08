import pandas as pd
import glob
from pathlib import Path
import matplotlib.pyplot as plt

# ============================================================
# CONFIGURATION
# ============================================================

SCENARIO_ID = 1

SCRIPT_DIR = Path(__file__).resolve().parent

BASE_FOLDER = (
    SCRIPT_DIR
    / ".." / ".."
    / "test_data" / "results" / "tls_performance"
).resolve()

SAVE_DIR = Path(
    rf"C:\Users\marie\OneDrive\Documents\Fernuni\Masterarbeit\Plots\Szenario_{SCENARIO_ID}_Raspi"
)
   
SAVE_DIR.mkdir(parents=True, exist_ok=True)

# Szenarien wie in deinem bestehenden Code
SCENARIOS = {
    1: {
        "Desktop-PC": BASE_FOLDER / "machine_1111" / "handshake_results",
        "Raspberry Pi": BASE_FOLDER / "machine_1" / "handshake_results",
    },
    2: {
        "Desktop-PC": BASE_FOLDER / "machine_22222" / "handshake_results",
        "Raspberry Pi": BASE_FOLDER / "machine_2" / "handshake_results",
    },
    3: {
        "Desktop-PC": BASE_FOLDER / "machine_3333" / "handshake_results",
        "Raspberry Pi": BASE_FOLDER / "machine_3" / "handshake_results",
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

# ============================================================
# DATA COLLECTION
# ============================================================

def collect_handshakes(base_path: Path, mode: str) -> pd.Series:
    dfs = []

    if mode == "classic":
        files = glob.glob(str(base_path / "classic" / "classic_results_run_*.csv"))
        for f in files:
            df = pd.read_csv(f)
            df = df[df["Reused Session ID"].isna()]
            df = df[df["Ciphersuite"] == CLASSIC_CS]
            df = df[df["Classic Algorithm"].isin(CLASSIC_ALGOS)]
            dfs.append(df["Connections in Real Time"])

    elif mode == "pq":
        for algo in PQ_ALGOS:
            files = glob.glob(str(base_path / "pqc" / algo / f"tls_handshake_{algo}_run_*.csv"))
            for f in files:
                df = pd.read_csv(f)
                df = df[df["Reused Session ID"].isna()]
                df = df[df["KEM Algorithm"] == PQ_KEM]
                dfs.append(df["Connections in Real Time"])

    else:
        raise ValueError(mode)

    return pd.concat(dfs, ignore_index=True)


def collect_time_per_handshake(
    base_path: Path,
    mode: str,
    time_col: str,
    conn_col: str
) -> pd.Series:
    dfs = []

    if mode == "classic":
        files = glob.glob(str(base_path / "classic" / "classic_results_run_*.csv"))
        for f in files:
            df = pd.read_csv(f)
            df = df[df["Reused Session ID"].isna()]
            df = df[df["Ciphersuite"] == CLASSIC_CS]
            df = df[df["Classic Algorithm"].isin(CLASSIC_ALGOS)]
            dfs.append(df[time_col] / df[conn_col])

    elif mode == "pq":
        for algo in PQ_ALGOS:
            files = glob.glob(str(base_path / "pqc" / algo / f"tls_handshake_{algo}_run_*.csv"))
            for f in files:
                df = pd.read_csv(f)
                df = df[df["Reused Session ID"].isna()]
                df = df[df["KEM Algorithm"] == PQ_KEM]
                dfs.append(df[time_col] / df[conn_col])

    else:
        raise ValueError(mode)

    return pd.concat(dfs, ignore_index=True)

# ============================================================
# AGGREGATION
# ============================================================

def build_summary(metric: str) -> pd.DataFrame:
    rows = []

    for platform_label, base_path in SCENARIOS[SCENARIO_ID].items():
        for mode in ["classic", "pq"]:
            if metric == "handshakes":
                values = collect_handshakes(base_path, mode)

            elif metric == "user_time":
                values = collect_time_per_handshake(
                    base_path,
                    mode,
                    time_col="User Time (s)",
                    conn_col="Connections in User Time"
                )

            elif metric == "real_time":
                values = collect_time_per_handshake(
                    base_path,
                    mode,
                    time_col="Real Time (s)",
                    conn_col="Connections in Real Time"
                )

            else:
                raise ValueError(metric)

            rows.append({
                "Platform": platform_label,
                "Mode": "Classic" if mode == "classic" else "Post-Quantum",
                "Median": values.median()
            })

    return pd.DataFrame(rows)

# ============================================================
# PLOTTING
# ============================================================

def plot_bar(df: pd.DataFrame, title: str, ylabel: str, filename: str):
    fig, ax = plt.subplots(figsize=(7, 4))

    order = [
        ("Desktop-PC", "Classic"),
        ("Desktop-PC", "Post-Quantum"),
        ("Raspberry Pi", "Classic"),
        ("Raspberry Pi", "Post-Quantum"),
    ]

    values = [
        df[(df.Platform == p) & (df.Mode == m)]["Median"].iloc[0]
        for p, m in order
    ]
    labels = [f"{p}\n{m}" for p, m in order]

    ax.bar(labels, values)
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.grid(axis="y", linestyle=":", alpha=0.6)

    plt.tight_layout()
    plt.savefig(SAVE_DIR / filename, dpi=300)
    plt.show()

# ============================================================
# TABLE
# ============================================================   
def build_platform_comparison_block(metric: str) -> pd.DataFrame:
    """
    Erstellt einen Tabellenblock im Format:
    Plattformvergleich | Klassisch | Post-Quantum
    """

    summary = build_summary(metric)

    rows = []

    for label in ["Desktop Median", "Raspberry Pi Median", "Faktor Raspi / Desktop"]:
        row = {"Plattformvergleich": label}

        for mode in ["Classic", "Post-Quantum"]:
            desktop = summary[
                (summary.Platform == "Desktop-PC") &
                (summary.Mode == mode)
            ]["Median"].iloc[0]

            raspi = summary[
                (summary.Platform == "Raspberry Pi") &
                (summary.Mode == mode)
            ]["Median"].iloc[0]

            if label == "Desktop Median":
                value = desktop
            elif label == "Raspberry Pi Median":
                value = raspi
            else:  # Faktor
                value = raspi / desktop

            row[mode] = value

        rows.append(row)

    return pd.DataFrame(rows)

def build_full_platform_comparison_table() -> pd.DataFrame:
    blocks = []

    metric_names = {
        "handshakes": "TLS-Handshakes (61 s)",
        "user_time": "Median User Time pro Handshake (s)",
        "real_time": "Median Real Time pro Handshake (s)",
    }

    for metric, title in metric_names.items():
        block = build_platform_comparison_block(metric)

        # Leere Zeile mit Metrik-Überschrift einfügen
        header = pd.DataFrame([{
            "Plattformvergleich": title,
            "Classic": "",
            "Post-Quantum": ""
        }])

        blocks.append(header)
        blocks.append(block)

    return pd.concat(blocks, ignore_index=True)

def save_platform_comparison_table():
    df = build_full_platform_comparison_table()
    path = SAVE_DIR / f"scenario{SCENARIO_ID}_platform_comparison_table.csv"
    df.to_csv(path, index=False, float_format="%.3f")
    print(f"Tabelle gespeichert unter: {path}")


# ============================================================
# MAIN
# ============================================================

def main():
    df_handshakes = build_summary("handshakes")
    plot_bar(
        df_handshakes,
        title=f"TLS-Handshake-Durchsatz (Szenario {SCENARIO_ID})",
        ylabel="Abgeschlossene TLS-Handshakes in 61 s",
        filename=f"scenario{SCENARIO_ID}_handshakes_platform_comparison.png"
    )

    df_user = build_summary("user_time")
    plot_bar(
        df_user,
        title=f"Median User Time pro TLS-Handshake (Szenario {SCENARIO_ID})",
        ylabel="Zeit pro Handshake (s)",
        filename=f"scenario{SCENARIO_ID}_median_user_time_platform_comparison.png"
    )

    df_real = build_summary("real_time")
    plot_bar(
        df_real,
        title=f"Median Real Time pro TLS-Handshake (Szenario {SCENARIO_ID})",
        ylabel="Zeit pro Handshake (s)",
        filename=f"scenario{SCENARIO_ID}_median_real_time_platform_comparison.png"
    )
    # create table
    save_platform_comparison_table()


if __name__ == "__main__":
    main()
