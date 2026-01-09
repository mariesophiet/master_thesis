import pandas as pd
import glob
import numpy as np
import os

# Ordner mit den Run-CSV-Dateien
folder_path = "../../test_data/results/tls_performance/machine_1111/handshake_results/classic"  # anpassen
output_file = os.path.join(folder_path, "aggregated_stats.csv")

# Alle CSV-Dateien im Ordner, außer die avg-Datei
csv_files = [f for f in glob.glob(os.path.join(folder_path, "*.csv"))
             if "avg" not in os.path.basename(f)]

# Liste zum Speichern aller Daten
all_data = []

# CSV-Dateien einlesen
for file in csv_files:
    df = pd.read_csv(file)
    all_data.append(df)

# Alle Daten zusammenführen
combined_df = pd.concat(all_data, ignore_index=True)

# Metriken, die statistisch ausgewertet werden sollen
metrics = ['Connections in User Time', 'User Time (s)',
           'Connections Per User Second', 'Connections in Real Time', 'Real Time (s)']

# Ergebnisliste
results = []

# Gruppieren nach Cipher + Algorithm
grouped = combined_df.groupby(['Ciphersuite', 'Classic Algorithm'])

for (cipher, algo), group in grouped:
    for metric in metrics:
        values = group[metric].values
        median = np.median(values)
        p25 = np.percentile(values, 25)
        p75 = np.percentile(values, 75)
        p95 = np.percentile(values, 95)
        std = np.std(values, ddof=1)  # Stichproben-Std

        results.append({
            'Ciphersuite': cipher,
            'Classic Algorithm': algo,
            'Metric': metric,
            'Median': median,
            'P25': p25,
            'P75': p75,
            'P95': p95,
            'Std': std
        })

# Ergebnis-DataFrame erstellen
result_df = pd.DataFrame(results)

# In CSV speichern
result_df.to_csv(output_file, index=False)

print(f"Aggregierte Statistik in {output_file} gespeichert.")