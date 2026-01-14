import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

# ============================================================
# Szenario wählen
# ============================================================
scenario = "1"
SCRIPT_DIR = Path(__file__).resolve().parent

desktop_csv = SCRIPT_DIR / ".." / ".." / "plots" / f"scenario_{scenario}" / "reused_vs_nonreused_values_MLKEM1024.csv"
raspi_csv   = SCRIPT_DIR / ".." / ".." / "plots" / f"scenario_{scenario}_raspi" / "reused_vs_nonreused_values_MLKEM1024.csv"

# ============================================================
# CSVs laden und Hardware-Spalte ergänzen
# ============================================================
df_desktop = pd.read_csv(desktop_csv)
df_desktop["Hardware"] = "Desktop"

df_raspi = pd.read_csv(raspi_csv)
df_raspi["Hardware"] = "Raspi"

# ============================================================
# Zusammenfügen
# ============================================================
df = pd.concat([df_desktop, df_raspi], ignore_index=True)

# ============================================================
# Daten für Full vs Reused umformen
# ============================================================
df_long = pd.melt(
    df,
    id_vars=["Algorithm", "Type", "Hardware", "Metric"],
    value_vars=["Full", "Reused"],
    var_name="Session",
    value_name="Value"
)

# ============================================================
# Hardwarevergleich-Plot
# ============================================================
def plot_hardware_comparison(df_long, metric_name, scenario, output_file=None):
    df_metric = df_long[df_long["Metric"] == metric_name]
    algos = df_metric["Algorithm"].unique()
    x = np.arange(len(algos))
    width = 0.2  # Balkenbreite

    fig, ax = plt.subplots(figsize=(12, 6))

    # Desktop Full
    ax.bar(x - 1.5*width,
           df_metric[(df_metric["Hardware"]=="Desktop") & (df_metric["Session"]=="Full")]["Value"],
           width, label="Desktop Full", color="skyblue")

    # Desktop Reused
    ax.bar(x - 0.5*width,
           df_metric[(df_metric["Hardware"]=="Desktop") & (df_metric["Session"]=="Reused")]["Value"],
           width, label="Desktop Reused", color="dodgerblue")

    # Raspi Full
    ax.bar(x + 0.5*width,
           df_metric[(df_metric["Hardware"]=="Raspi") & (df_metric["Session"]=="Full")]["Value"],
           width, label="Raspi Full", color="lightcoral")

    # Raspi Reused
    ax.bar(x + 1.5*width,
           df_metric[(df_metric["Hardware"]=="Raspi") & (df_metric["Session"]=="Reused")]["Value"],
           width, label="Raspi Reused", color="red")

    ax.set_xticks(x)
    ax.set_xticklabels(algos, rotation=30)
    ax.set_xlabel("Signaturalgorithmus")
    ax.set_ylabel(metric_name)
    ax.set_title(f"Hardwarevergleich Desktop vs Raspberry Pi ({metric_name}) Szenario {scenario}")
    ax.legend()
    plt.tight_layout()
    
    if output_file:
        plt.savefig(output_file, dpi=300)
        print(f"Plot gespeichert unter: {output_file}")
    plt.show()

# ============================================================
# Plot für alle Metriken erstellen
# ============================================================
for metric in df["Metric"].unique():
    output_file = SCRIPT_DIR / ".." / ".." / "plots" / f"scenario_{scenario}_raspi" / f"hardware_comparison_{metric}.png"
    plot_hardware_comparison(df_long, metric, scenario, output_file)

# ============================================================
# Hardwarevergleich-Tabelle mit prozentualen Änderungen erstellen
# ============================================================

# Pivot-Tabelle erstellen, sodass Desktop und Raspi Spalten werden
df_table = df_long.pivot_table(
    index=["Algorithm", "Metric", "Session"],
    columns="Hardware",
    values="Value"
).reset_index()

# Prozentuale Änderung von Desktop -> Raspi berechnen
df_table["Change_%"] = ((df_table["Raspi"] - df_table["Desktop"]) / df_table["Desktop"]) * 100

# Schöne Spaltenreihenfolge
df_table = df_table[["Algorithm", "Metric", "Session", "Desktop", "Raspi", "Change_%"]]

# Tabelle ausgeben
print("\n=== Hardwarevergleich-Tabelle mit Prozentänderungen ===")
print(df_table)

# Tabelle als CSV speichern
output_table_file = SCRIPT_DIR / ".." / ".." / "plots" / f"scenario_{scenario}_raspi" / "hardware_comparison_table.csv"
df_table.to_csv(output_table_file, index=False)
print(f"Tabelle gespeichert unter: {output_table_file}")
