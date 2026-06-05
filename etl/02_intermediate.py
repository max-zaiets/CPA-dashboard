"""
02_intermediate.py — промежуточные таблицы из очищенных источников.

Таблицы:
  int_leads          — регистрации и логины по partner_id + country
  int_sales          — CPA-продажи из keitaro
  int_retention_rev  — retention-доход из keitaro
  int_cpa            — затраты CPA из affise
  int_email_cost     — стоимость email-коммуникаций
  int_sms_cost       — стоимость SMS-коммуникаций (UAH -> USD)
  int_adsense        — adsense-доход из GA4
"""
import pandas as pd
from pathlib import Path

RAW = Path(__file__).parent.parent / "output" / "raw"
OUT = Path(__file__).parent.parent / "output" / "intermediate"

UAH_TO_USD = 41.0

RETENTION_TYPES = {"email", "sms", "push", "trafficback", "push-pwa"}

# Валидные campaign_group и ts для каждой страны
VALID_CAMPAIGN_GROUPS = {
    "mx": {"Broker MX", "Finance MX"},
    "co": {"Broker CO", "Finance CO"},
    "es": {"Broker ES", "Finance ES"},
    "ro": {"Broker RO", "Finance RO"},
    "ph": {"Broker PH", "Finance PH"},
    "vn": {"Broker VN", "Finance VN"},
}
ALL_VALID_CAMPAIGN_GROUPS = {cg for groups in VALID_CAMPAIGN_GROUPS.values() for cg in groups}

VALID_TS = {
    "mx": {"Broker MX"},
    "co": {"Broker CO"},
    "es": {"Broker ES"},
    "ro": {"Broker RO"},
    "ph": {"Broker PH"},
    "vn": {"Broker VN"},
}
ALL_VALID_TS = {ts for groups in VALID_TS.values() for ts in groups}

VALID_UTM = {"CPA", "google", "facebook", "tiktok", "bigo", "bing", "zalo"}


def _last_utm_before_date(
    events_df: pd.DataFrame, event_date_col: str, crm_col: str, lead_params: pd.DataFrame
) -> pd.Series:
    lp = (
        lead_params[["crm_id", "created_at", "utm_source"]]
        .rename(columns={"crm_id": "_crm", "created_at": "_dt"})
        .sort_values("_dt")
    )
    left = (
        events_df[[crm_col, event_date_col]]
        .copy()
        .reset_index()
        .rename(columns={crm_col: "_crm", event_date_col: "_dt"})
        .sort_values("_dt")
    )
    merged = pd.merge_asof(left, lp, on="_dt", by="_crm", direction="backward")
    return merged.set_index("index")["utm_source"]


def _lookup_rate_by_date(events: pd.DataFrame, rates: pd.DataFrame, date_col: str) -> pd.Series:
    events_sorted = events[[date_col]].copy().sort_values(date_col).reset_index()
    rates_sorted = rates.sort_values("dt_from")

    merged = pd.merge_asof(
        events_sorted,
        rates_sorted,
        left_on=date_col,
        right_on="dt_from",
        direction="backward",
    )
    # Обнуляем строки вышедшие за правую границу интервала
    merged.loc[merged[date_col] >= merged["dt_to"], "cost_usd"] = None
    return merged.set_index("index")["cost_usd"]


def _lookup_sms_rate(events: pd.DataFrame, sms_rates: pd.DataFrame) -> pd.Series:
    result = []
    for country, group in events.groupby("country"):
        country_rates = sms_rates[sms_rates["country"] == country].sort_values("dt_from")
        group_sorted = group[["date"]].sort_values("date").reset_index()
        merged = pd.merge_asof(
            group_sorted,
            country_rates,
            left_on="date",
            right_on="dt_from",
            direction="backward",
        )
        merged.loc[merged["date"] >= merged["dt_to"], "cost_uah"] = None
        result.append(merged.set_index("index")["cost_uah"])
    return pd.concat(result).reindex(events.index)


def build_int_leads(lead_params: pd.DataFrame) -> pd.DataFrame:
    leads = lead_params[lead_params["action"].isin(["registration", "login"])].copy()
    return (
        leads.groupby(["affid", "country"])
        .agg(
            registrations=("action", lambda x: (x == "registration").sum()),
            all_leads=("action", "count"),
        )
        .reset_index()
        .rename(columns={"affid": "partner_id"})
    )


def build_int_sales(keitaro: pd.DataFrame) -> pd.DataFrame:
    sales = keitaro[
        (keitaro["sub_id_4"] == "CPA")
        & (keitaro["status"] == "sale")
        & (keitaro["campaign_group"].isin(ALL_VALID_CAMPAIGN_GROUPS))
        & (keitaro["ts"].isin(ALL_VALID_TS))
    ].copy()
    return (
        sales.groupby(["sub_id_5", "country"])
        .agg(sales=("conversion_id", "count"), revenue=("revenue", "sum"))
        .reset_index()
        .rename(columns={"sub_id_5": "partner_id"})
    )


def build_int_retention_rev(keitaro: pd.DataFrame, lead_params: pd.DataFrame) -> pd.DataFrame:
    retention = keitaro[
        keitaro["sub_id_4"].isin(RETENTION_TYPES)
        & (keitaro["status"] == "sale")
        & (keitaro["campaign_group"].isin(ALL_VALID_CAMPAIGN_GROUPS))
        & (keitaro["ts"].isin(ALL_VALID_TS))
    ].copy()
    # Атрибуция по последнему utm_source перед датой продажи
    retention["_utm"] = _last_utm_before_date(retention, "created_at", "sub_id_7", lead_params)
    retention = retention[retention["_utm"].isin(VALID_UTM) & (retention["_utm"] == "CPA")]
    # Получаем affid через sub_id_7 = crm_id
    lead_info = lead_params[lead_params["affid"].notna()][["crm_id", "affid"]].drop_duplicates("crm_id")
    retention = retention.merge(lead_info, left_on="sub_id_7", right_on="crm_id", how="left")
    return (
        retention.groupby(["affid", "country"])
        .agg(retention_revenue=("revenue", "sum"))
        .reset_index()
        .rename(columns={"affid": "partner_id"})
    )


def build_int_cpa(affise: pd.DataFrame) -> pd.DataFrame:
    cpa = affise[affise["status"] == 1].copy()
    return (
        cpa.groupby(["partner_full_id", "country"])
        .agg(cost_cpa=("revenue", "sum"))
        .reset_index()
        .rename(columns={"partner_full_id": "partner_id"})
    )


def build_int_email_cost(
    scenario_log: pd.DataFrame, lead_params: pd.DataFrame, email_rates: pd.DataFrame
) -> pd.DataFrame:
    emails = scenario_log[scenario_log["action"] == "email"].copy()
    lead_info = lead_params[lead_params["affid"].notna()][["crm_id", "affid", "country"]].drop_duplicates("crm_id")
    emails = emails.merge(lead_info, left_on="subid", right_on="crm_id", how="inner")
    # Только события где последний utm_source = CPA
    emails["_utm"] = _last_utm_before_date(emails, "date", "subid", lead_params)
    emails = emails[emails["_utm"].isin(VALID_UTM) & (emails["_utm"] == "CPA")]

    emails["cost_usd"] = _lookup_rate_by_date(emails, email_rates, "date")

    return (
        emails.groupby(["affid", "country"])
        .agg(cost_email=("cost_usd", "sum"))
        .reset_index()
        .rename(columns={"affid": "partner_id"})
    )


def build_int_sms_cost(
    scenario_log: pd.DataFrame, lead_params: pd.DataFrame, sms_rates: pd.DataFrame
) -> pd.DataFrame:
    sms = scenario_log[scenario_log["action"] == "sms"].copy()
    lead_info = lead_params[lead_params["affid"].notna()][["crm_id", "affid", "country"]].drop_duplicates("crm_id")
    sms = sms.merge(lead_info, left_on="subid", right_on="crm_id", how="inner")
    # Только события где последний utm_source = CPA
    sms["_utm"] = _last_utm_before_date(sms, "date", "subid", lead_params)
    sms = sms[sms["_utm"].isin(VALID_UTM) & (sms["_utm"] == "CPA")]

    sms["cost_uah"] = _lookup_sms_rate(sms, sms_rates)
    sms["cost_usd"] = sms["cost_uah"] / UAH_TO_USD

    return (
        sms.groupby(["affid", "country"])
        .agg(cost_sms=("cost_usd", "sum"))
        .reset_index()
        .rename(columns={"affid": "partner_id"})
    )


def build_int_adsense(ga4: pd.DataFrame) -> pd.DataFrame:
    adsense = ga4[
        (ga4["event_name"] == "ad_impression") & (ga4["aff_id"] != "(not set)")
    ].copy()
    return (
        adsense.groupby(["aff_id", "country"])
        .agg(adsense_revenue=("total_revenue", "sum"))
        .reset_index()
        .rename(columns={"aff_id": "partner_id"})
    )


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)

    lead_params = pd.read_parquet(RAW / "lead_params.parquet")
    scenario_log = pd.read_parquet(RAW / "scenario_log.parquet")
    keitaro = pd.read_parquet(RAW / "keitaro.parquet")
    affise = pd.read_parquet(RAW / "affise.parquet")
    ga4 = pd.read_parquet(RAW / "ga4.parquet")
    email_rates = pd.read_parquet(RAW / "email_rates.parquet")
    sms_rates = pd.read_parquet(RAW / "sms_rates.parquet")

    tables = {
        "int_leads": build_int_leads(lead_params),
        "int_sales": build_int_sales(keitaro),
        "int_retention_rev": build_int_retention_rev(keitaro, lead_params),
        "int_cpa": build_int_cpa(affise),
        "int_email_cost": build_int_email_cost(scenario_log, lead_params, email_rates),
        "int_sms_cost": build_int_sms_cost(scenario_log, lead_params, sms_rates),
        "int_adsense": build_int_adsense(ga4),
    }

    for name, df in tables.items():
        path = OUT / f"{name}.parquet"
        df.to_parquet(path, index=False)
        print(f"  {name}: {df.shape[0]} rows -> {path.name}")
        print(df.head(3).to_string(index=False))
        print()

    print("Done: 02_intermediate.py")
