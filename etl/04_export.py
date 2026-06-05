"""
04_export.py — экспорт финального датасета в CSV для Google Sheets / Looker Studio.
"""
import pandas as pd
from pathlib import Path

OUT = Path(__file__).parent.parent / "output"


if __name__ == "__main__":
    mart = pd.read_parquet(OUT / "mart_dashboard.parquet")
    mart.insert(1, "network_id", mart["partner_id"].str.split("_").str[0])
    csv_path = OUT / "dashboard_final.csv"
    mart.to_csv(csv_path, index=False, sep=";", decimal=",", encoding="utf-8-sig")
    print(f"Exported {mart.shape[0]} rows -> {csv_path}")
    print("Done: 04_export.py")
