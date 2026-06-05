"""
01_load.py — загрузка всех CSV-источников, парсинг дат, сохранение в parquet.
"""
import pandas as pd
from pathlib import Path

SRC = Path(__file__).parent.parent / "src"
OUT = Path(__file__).parent.parent / "output" / "raw"


def load_all() -> dict[str, pd.DataFrame]:
    OUT.mkdir(parents=True, exist_ok=True)

    lead_params = pd.read_csv(SRC / "lead_params (3).csv", sep=";")
    lead_params["created_at"] = pd.to_datetime(
        lead_params["created_at"], format="%d-%m-%Y %H:%M:%S"
    )

    scenario_log = pd.read_csv(SRC / "scenario_log.csv", sep=";")
    scenario_log["date"] = pd.to_datetime(scenario_log["date"], format="%d-%m-%Y")

    keitaro = pd.read_csv(SRC / "mock export keitaro.csv", sep=";")
    keitaro["created_at"] = pd.to_datetime(keitaro["created_at"])

    affise = pd.read_csv(SRC / "mock export affise.csv", sep=";")
    affise["created_at"] = pd.to_datetime(affise["created_at"])

    ga4 = pd.read_csv(SRC / "mock export ga4_adsense.csv", sep=";")
    ga4["date"] = pd.to_datetime(ga4["date"])

    email_rates = pd.read_csv(SRC / "email_rates.csv", sep=";").rename(
        columns={"dt_from (>=)": "dt_from", "dt_to (<)": "dt_to"}
    )
    email_rates["dt_from"] = pd.to_datetime(email_rates["dt_from"])
    email_rates["dt_to"] = pd.to_datetime(email_rates["dt_to"])

    sms_rates = pd.read_csv(SRC / "sms_rates.csv", sep=";").rename(
        columns={"dt_from (>=)": "dt_from", "dt_to (<)": "dt_to"}
    )
    sms_rates["dt_from"] = pd.to_datetime(sms_rates["dt_from"])
    sms_rates["dt_to"] = pd.to_datetime(sms_rates["dt_to"])

    return {
        "lead_params": lead_params,
        "scenario_log": scenario_log,
        "keitaro": keitaro,
        "affise": affise,
        "ga4": ga4,
        "email_rates": email_rates,
        "sms_rates": sms_rates,
    }


if __name__ == "__main__":
    dfs = load_all()
    for name, df in dfs.items():
        path = OUT / f"{name}.parquet"
        df.to_parquet(path, index=False)
        print(f"  {name}: {df.shape[0]} rows, {df.shape[1]} cols -> {path.name}")
    print("Done: 01_load.py")
