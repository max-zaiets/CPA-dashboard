# CPA Dashboard — Pipeline

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                           ИСТОЧНИКИ ДАННЫХ                                  ║
╠══════════════╦══════════════╦══════════════╦══════════════╦══════════════════╣
║  lead_params ║ scenario_log ║    affise    ║   keitaro    ║    ga4_adsense   ║
║     (CRM)    ║    (CRM)     ║  (Cost CPA)  ║  (Sales /    ║ (Adsense Revenue)║
║              ║              ║              ║   Revenue)   ║                  ║
╠══════════════╩══════════════╩══════════════╩══════════════╩══════════════════╣
║          email_rates.csv          sms_rates.csv                              ║
║          (тарифы email, USD)      (тарифы SMS, UAH)                          ║
╚══════════════════════════════════════════════════════════════════════════════╝
                                    │
                                    ▼ 01_load.py
╔══════════════════════════════════════════════════════════════════════════════╗
║                              RAW LAYER                                       ║
║         CSV → Parquet (без изменений, нормализация имён колонок)             ║
╚══════════════════════════════════════════════════════════════════════════════╝
                                    │
                                    ▼ 02_intermediate.py
╔══════════════════════════════════════════════════════════════════════════════╗
║                          INTERMEDIATE LAYER                                  ║
║                                                                              ║
║  int_leads          int_sales        int_retention_rev      int_cpa          ║
║  ───────────        ───────────      ────────────────       ───────────      ║
║  lead_params        keitaro          keitaro                affise           ║
║  registrations      sub_id_4=CPA     sub_id_4=email/sms     status=1        ║
║  + logins           status=sale      status=sale            SUM(revenue)     ║
║  по partner_id      ts+campaign      utm_source=CPA         → cost_cpa       ║
║                     group фильтр     атрибуция                               ║
║                                                                              ║
║  int_email_cost     int_sms_cost     int_adsense                             ║
║  ───────────────    ────────────     ───────────                             ║
║  scenario_log       scenario_log     ga4                                     ║
║  action=email       action=sms       event=ad_impression                    ║
║  utm_source=CPA     utm_source=CPA   SUM(total_revenue)                     ║
║  × email_rate       × sms_rate÷41   → adsense_revenue                       ║
║                                                                              ║
║              Все таблицы → partner_id | country | метрика                   ║
╚══════════════════════════════════════════════════════════════════════════════╝
                                    │
                                    ▼ 03_mart.py
╔══════════════════════════════════════════════════════════════════════════════╗
║                              MART LAYER                                      ║
║                                                                              ║
║   JOIN по ключу: partner_id + country                                        ║
║                                                                              ║
║   partner_id │ country │ registrations │ all_leads │ unique_pct │ sales │   ║
║   cr_pct │ revenue │ cost_cpa │ profit │ romi_new_user │                     ║
║   retention_revenue │ cost_email │ cost_sms │ retention_cost │              ║
║   retention_profit │ romi_retention │ adsense_revenue │                     ║
║   revenue_tot │ cost_tot │ profit_tot │ gpm_pct │ romi_tot                  ║
║                                                                              ║
║                        18 строк × 26 колонок                                ║
╚══════════════════════════════════════════════════════════════════════════════╝
                                    │
                                    ▼ 04_export.py
╔══════════════════════════════════════════════════════════════════════════════╗
║                               EXPORT                                         ║
║                                                                              ║
║   dashboard_final.csv  →  Google Sheets  →  Looker Studio                   ║
║   (sep=";", decimal=",")                                                     ║
╚══════════════════════════════════════════════════════════════════════════════╝
```
