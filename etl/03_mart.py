"""
03_mart.py — финальный джойн промежуточных таблиц и расчёт всех метрик.

Выходная таблица: mart_dashboard (partner_id + country как составной ключ)
"""
import pandas as pd
from pathlib import Path

INT = Path(__file__).parent.parent / "output" / "intermediate"
OUT = Path(__file__).parent.parent / "output"


def build_mart() -> pd.DataFrame:
    int_leads = pd.read_parquet(INT / "int_leads.parquet")
    int_sales = pd.read_parquet(INT / "int_sales.parquet")
    int_retention_rev = pd.read_parquet(INT / "int_retention_rev.parquet")
    int_cpa = pd.read_parquet(INT / "int_cpa.parquet")
    int_email_cost = pd.read_parquet(INT / "int_email_cost.parquet")
    int_sms_cost = pd.read_parquet(INT / "int_sms_cost.parquet")
    int_adsense = pd.read_parquet(INT / "int_adsense.parquet")

    mart = int_leads.copy()
    for df in [int_sales, int_retention_rev, int_cpa, int_email_cost, int_sms_cost, int_adsense]:
        mart = mart.merge(df, on=["partner_id", "country"], how="left")

    # Заполняем нули там где у партнёра нет данных по источнику
    numeric_cols = [
        "registrations", "all_leads",
        "sales", "revenue",
        "retention_revenue",
        "cost_cpa",
        "cost_email", "cost_sms",
        "adsense_revenue",
    ]
    mart[numeric_cols] = mart[numeric_cols].fillna(0)

    mart["unique_pct"] = mart["registrations"] / mart["all_leads"].replace(0, pd.NA) * 100
    mart["epl_primary"] = mart["revenue"] / mart["all_leads"].replace(0, pd.NA)
    mart["cr_pct"] = mart["sales"] / mart["all_leads"].replace(0, pd.NA) * 100

    mart["retention_cost"] = mart["cost_email"] + mart["cost_sms"]
    mart["retention_profit"] = mart["retention_revenue"] - mart["retention_cost"]
    mart["romi_retention"] = (
        mart["retention_profit"] / mart["retention_cost"].replace(0, pd.NA) * 100
    )

    mart["profit"] = mart["revenue"] - mart["cost_cpa"]
    mart["romi_new_user"] = mart["profit"] / mart["cost_cpa"].replace(0, pd.NA) * 100

    mart["revenue_tot"] = mart["revenue"] + mart["retention_revenue"] + mart["adsense_revenue"]
    mart["cost_tot"] = mart["cost_cpa"] + mart["retention_cost"]
    mart["profit_tot"] = mart["revenue_tot"] - mart["cost_tot"]
    mart["romi_tot"] = mart["profit_tot"] / mart["cost_tot"].replace(0, pd.NA) * 100

    mart["epl_total"] = mart["revenue_tot"] / mart["all_leads"].replace(0, pd.NA)
    mart["gpm_pct"] = mart["profit_tot"] / mart["revenue_tot"].replace(0, pd.NA) * 100

    # Округляем float-колонки для читаемости
    float_cols = mart.select_dtypes("float").columns
    mart[float_cols] = mart[float_cols].round(4)

    # Порядок колонок
    col_order = [
        "partner_id", "country",
        "registrations", "all_leads", "unique_pct",
        "epl_primary", "epl_total",
        "sales", "cr_pct",
        "revenue", "cost_cpa", "profit", "romi_new_user",
        "retention_revenue", "cost_email", "cost_sms", "retention_cost",
        "retention_profit", "romi_retention",
        "adsense_revenue",
        "revenue_tot", "cost_tot", "profit_tot", "gpm_pct", "romi_tot",
    ]
    return mart[col_order]


if __name__ == "__main__":
    mart = build_mart()
    path = OUT / "mart_dashboard.parquet"
    mart.to_parquet(path, index=False)
    print(f"mart_dashboard: {mart.shape[0]} rows x {mart.shape[1]} cols")
    print(mart.to_string(index=False))
    print(f"\nSaved -> {path}")
    print("Done: 03_mart.py")
