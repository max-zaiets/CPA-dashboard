RUS TRANSLATION BELOW

# CPA Traffic Performance Dashboard

A multi-source ETL pipeline and BI dashboard that consolidates **CPA (Cost-Per-Action) affiliate traffic** from 5 different platforms into a single calculation model — surfacing revenue, cost, profit and **ROMI** per `Partner ID` and country.

![Python](https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=white)
![pandas](https://img.shields.io/badge/pandas-150458?logo=pandas&logoColor=white)
![SQL](https://img.shields.io/badge/SQL-4479A1?logo=postgresql&logoColor=white)
![BigQuery](https://img.shields.io/badge/BigQuery-669DF6?logo=googlebigquery&logoColor=white)
![Looker Studio](https://img.shields.io/badge/Looker%20Studio-4285F4?logo=looker&logoColor=white)

**📊 [Live Dashboard (Looker Studio)](https://datastudio.google.com/u/0/reporting/aba907c8-445f-4a0a-8f17-d5a48e88ad46/page/TmCzF)**

---

## Table of Contents

- [Overview](#overview)
- [Data Sources](#data-sources)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Intermediate Tables](#intermediate-tables)
- [Metrics and Business Logic](#metrics-and-business-logic)
- [Key Technical Decisions](#key-technical-decisions)
- [Results](#results)
- [Assumptions and Open Questions](#assumptions-and-open-questions)
- [Known Limitations](#known-limitations)
- [Production Roadmap](#production-roadmap)

---

## Overview

The goal is to design and implement a dashboard measuring CPA-traffic performance by `Partner ID`, broken down across countries, revenue, costs, profit and ROMI. The core challenge is **joining data from 5 sources into a single, consistent calculation model**.

---

## Data Sources

| Source | File | Provides | Partner ID key |
| --- | --- | --- | --- |
| CRM | `lead_params.csv` | Registrations, logins, `utm_source` | `affid` |
| CRM | `scenario_log.csv` | Email & SMS communications | via `crm_id` |
| Affise | `mock_export_affise.csv` | Cost CPA | `partner.id` + `"_"` + `affiliates_params5` |
| Keitaro | `mock_export_keitaro.csv` | Sales, Revenue, Retention Revenue | `sub_id_5` |
| Google Analytics 4 | `mock_export_ga4_adsense.csv` | Adsense Revenue | `aff_id` |
| Google Sheets | `email_rates.csv`, `sms_rates.csv` | Rate cards for cost calculation | — |

### Partner ID mapping

The unified join key across every source follows the format `{partner_id}_{affid}` — for example `104_56`:

```text
lead_params.affid                              = 104_56
keitaro.sub_id_5                               = 104_56
affise: partner.id + "_" + affiliates_params5  = 104_56
ga4.aff_id                                     = 104_56
```

---

## Architecture

A three-layer pipeline built on **Python + SQL**:

```text
RAW  (CSV → Parquet)
        ↓
INTERMEDIATE  (7 staging tables)
        ↓
MART  (final data mart — 18 rows × 26 columns)
        ↓
EXPORT  (dashboard_final.csv → Google Sheets → Looker Studio)
```

### ETL files

| File | Purpose |
| --- | --- |
| `etl/01_load.py` | Load CSV → Parquet, normalize column names |
| `etl/02_intermediate.py` | Build the 7 staging tables |
| `etl/03_mart.py` | Final join + computation of all metrics |
| `etl/04_export.py` | Export to CSV (`sep=";"`, `decimal=","`) |

### SQL equivalents for BigQuery

Every staging table and the final `SELECT` are also reproduced in `sql/` for a production implementation on **BigQuery**.

---

## Project Structure

```text
.
├── etl/
│   ├── 01_load.py            # CSV → Parquet, column-name normalization
│   ├── 02_intermediate.py    # 7 staging tables
│   ├── 03_mart.py            # Final join + all metric calculations
│   └── 04_export.py          # Export to CSV (sep=";", decimal=",")
├── sql/
│   ├── intermediate/         # BigQuery views for each staging table
│   └── mart/
│       └── final_view.sql    # Production mart view
├── output/
│   └── dashboard_final.csv   # Final dataset (18 rows × 26 columns)
└── README.md
```

---

## Intermediate Tables

| Table | Source | Logic |
| --- | --- | --- |
| `int_leads` | `lead_params` | `action IN ('registration','login')`, grouped by `partner_id` + `country` |
| `int_sales` | `keitaro` | `sub_id_4='CPA'`, `status='sale'`, filtered on `ts` + `campaign_group` |
| `int_retention_rev` | `keitaro` + `lead_params` | `sub_id_4 IN (sms/email/push/…)`, `utm_source` attribution |
| `int_cpa` | `affise` | `status=1`, grouped by `partner_full_id` + `country` |
| `int_email_cost` | `scenario_log` + `lead_params` + `email_rates` | `action='email'`, `utm_source` attribution, range join on rate |
| `int_sms_cost` | `scenario_log` + `lead_params` + `sms_rates` | `action='sms'`, UAH→USD rate, range join on country and date |
| `int_adsense` | `ga4` | `event_name='ad_impression'`, grouped by `aff_id` + `country` |

---

## Metrics and Business Logic

### New User block

| Metric | Formula | Meaning |
| --- | --- | --- |
| Registrations | `COUNT(action='registration')` | Unique new leads |
| All Leads | `COUNT(action IN registration, login)` | All events, including repeats |
| Unique % | `Registrations / All Leads × 100` | Share of unique users in total traffic |
| EPL Primary | `Revenue / All Leads` | Earnings per lead |
| Sales | `COUNT` from Keitaro (CPA + sale) | Completed sales |
| CR % | `Sales / All Leads × 100` | Traffic-to-sale conversion rate |
| Revenue | `SUM(revenue)` from Keitaro | Revenue from new users |
| Cost CPA | `SUM(revenue)` from Affise | Acquisition cost |
| Profit | `Revenue − Cost CPA` | Profit on new users |
| ROMI % New User | `Profit / Cost CPA × 100` | Return on acquisition spend |

### Retention block

| Metric | Formula | Meaning |
| --- | --- | --- |
| Retention Revenue | `SUM(revenue)` from Keitaro (email/sms/push…) with CPA attribution | Revenue from repeat communications |
| Cost Email | `COUNT(email events) × rate` from `email_rates` | Email campaign cost |
| Cost SMS | `COUNT(sms events) × rate / 41` from `sms_rates` | SMS cost in USD |
| Retention Cost | `Cost Email + Cost SMS` | Total retention cost |
| Retention Profit | `Retention Revenue − Retention Cost` | Retention profit |
| ROMI % Retention | `Retention Profit / Retention Cost × 100` | Retention effectiveness |

### Total block

| Metric | Formula |
| --- | --- |
| EPL Total | `Revenue TOT / All Leads` |
| Adsense Revenue | `SUM(total_revenue)` from GA4 (`ad_impression`) |
| Revenue TOT | `Revenue + Retention Revenue + Adsense Revenue` |
| Cost TOT | `Cost CPA + Retention Cost` |
| Profit TOT | `Revenue TOT − Cost TOT` |
| GPM % | `Profit TOT / Revenue TOT × 100` |
| ROMI % TOT | `Profit TOT / Cost TOT × 100` |

---

## Key Technical Decisions

**`utm_source` attribution** — for Retention Revenue, Cost Email and Cost SMS, a last-touch model is applied: for each event, `pd.merge_asof` finds the most recent `utm_source` in `lead_params` before the event date. Only `CPA`, `google`, `facebook`, `tiktok`, `bigo`, `bing` and `zalo` are considered. Only events with `utm_source = CPA` reach the dashboard.

**Range join on rate cards** — the email/sms rate is resolved via `merge_asof` on the condition `dt_from <= event_date < dt_to`. For SMS, an additional filter by country is applied.

**Keitaro filtering** — `ts` and `campaign_group` filters are applied per country (e.g. `mx` → `Broker MX` / `Finance MX`). Rows with `campaign_group="Other"` and `revenue=999` are dropped as noise.

**UAH→USD conversion** — fixed rate of `1 USD = 41 UAH` (assumption — see [Assumptions](#assumptions-and-open-questions)).

---

## Results

The final dataset `output/dashboard_final.csv`:

- **18 rows** — one per unique partner
- **26 columns** — every metric from the spec + `network_id` for the hierarchical filter

The visualization is built in **Looker Studio** with filters by `Country`, `Partner ID` (`network_id`) and `Affid` (`partner_id`).

---

## Assumptions and Open Questions

| # | Question | Assumption |
| --- | --- | --- |
| 1 | UAH→USD rate for SMS not specified in the brief | Fixed rate `1 USD = 41 UAH` |
| 2 | Which date to use for the email/sms rate lookup | Event date from `scenario_log` |
| 3 | How to handle empty `aff_id` in GA4 | Exclude rows with `(not set)` |
| 4 | 6 leads with `affid=NaN` (`utm_source=google`) | Excluded from the CPA dashboard |
| 5 | Email/sms rate — per send or per 1,000? | Interpreted as per single send |
| 6 | Retention Revenue — CPA attribution only | google/facebook traffic not included |

---

## Known Limitations

**Date filtering** — the dashboard does not support correct filtering by date. The cause is architectural: leads, sales and costs are recorded across different sources on different dates (a lead arrives today and converts weeks later). Aggregating them into a single row under one date is impossible without breaking metric correctness.

> In production this is solved with **BigQuery date partitioning**: each source is filtered on its own native date at the SQL-query level, rather than on the pre-aggregated table.

**Readability** — 22 metrics in a single table are hard to read. In production, splitting into dedicated pages is recommended: *Leads/Affiliates*, *Keitaro (Sales + Retention)*, *Adsense*, *Overview*.

---

## Production Roadmap

1. Set up a BigQuery dataset + load the CRM tables (`lead_params`, `scenario_log`).
2. Connect the Affise API → scheduled export to BigQuery.
3. Connect the Keitaro API → scheduled export to BigQuery.
4. Connect GA4 → BigQuery export (native integration).
5. Load the rate tables (`email_rates`, `sms_rates`) as reference data in BigQuery.
6. Implement the intermediate views from `sql/intermediate/`.
7. Implement the final mart view (`sql/mart/final_view.sql`).
8. Connect Looker Studio to BigQuery → configure the dashboard.
9. Add the UAH→USD rate as a separate table with historical values (NBU API).





Ссылка на дашборд: https://datastudio.google.com/u/0/reporting/aba907c8-445f-4a0a-8f17-d5a48e88ad46/page/TmCzF
<img width="1920" height="1080" alt="Dashboard" src="https://github.com/user-attachments/assets/460072a0-e05a-473b-896e-d28d969b68d3" />


# CPA Dashboard
## Документация по реализации

---

## 1. Цель

Спроектировать и реализовать дашборд эффективности CPA-трафика по Partner ID в разрезе стран, доходов, затрат, прибыли и ROMI. Основная задача — свести данные из 5 источников в единую модель расчётов.

---

## 2. Источники данных

| Источник | Файл | Что даёт | Partner ID |
|---|---|---|---|
| CRM | `lead_params.csv` | Регистрации, логины, utm_source | `affid` |
| CRM | `scenario_log.csv` | Email и SMS коммуникации | через crm_id |
| Affise | `mock export affise.csv` | Cost CPA | `partner.id + "_" + affiliates_params5` |
| Keitaro | `mock export keitaro.csv` | Sales, Revenue, Retention Revenue | `sub_id_5` |
| Google Analytics 4 | `mock export ga4_adsense.csv` | Adsense Revenue | `aff_id` |
| Google Sheets | `email_rates.csv`, `sms_rates.csv` | Тарифы для расчёта затрат | — |

**Маппинг Partner ID** — единый ключ во всех источниках имеет формат `{partner_id}_{affid}`, например `104_56`:
- `lead_params.affid` = `104_56`
- `keitaro.sub_id_5` = `104_56`
- `affise: partner.id + "_" + affiliates_params5` = `104_56`
- `ga4.aff_id` = `104_56`

---

## 3. Архитектура решения

Реализован трёхслойный пайплайн на Python + SQL:

```
RAW (CSV → Parquet)
    ↓
INTERMEDIATE (7 промежуточных таблиц)
    ↓
MART (финальная витрина, 18 строк × 26 колонок)
    ↓
EXPORT (dashboard_final.csv → Google Sheets → Looker Studio)
```

### Файлы ETL

| Файл | Назначение |
|---|---|
| `etl/01_load.py` | Загрузка CSV → Parquet, нормализация имён колонок |
| `etl/02_intermediate.py` | 7 промежуточных таблиц |
| `etl/03_mart.py` | Финальный джойн + расчёт всех метрик |
| `etl/04_export.py` | Экспорт в CSV (sep=";", decimal=",") |

### SQL эквиваленты для BigQuery

Все промежуточные таблицы и финальный SELECT продублированы в `sql/` для продакшн-реализации через BigQuery.

---

## 4. Промежуточные таблицы

| Таблица | Источник | Логика |
|---|---|---|
| `int_leads` | lead_params | action IN ('registration','login'), группировка по partner_id + country |
| `int_sales` | keitaro | sub_id_4='CPA', status='sale', фильтры ts + campaign_group |
| `int_retention_rev` | keitaro + lead_params | sub_id_4 IN (sms/email/push/...), utm_source атрибуция |
| `int_cpa` | affise | status=1, группировка по partner_full_id + country |
| `int_email_cost` | scenario_log + lead_params + email_rates | action='email', utm_source атрибуция, range join по тарифу |
| `int_sms_cost` | scenario_log + lead_params + sms_rates | action='sms', тариф UAH→USD, range join по стране и дате |
| `int_adsense` | ga4 | event_name='ad_impression', группировка по aff_id + country |

---

## 5. Бизнес-логика метрик

### New User блок
| Метрика | Формула | Смысл |
|---|---|---|
| Registrations | COUNT(action='registration') | Уникальные новые лиды |
| All Leads | COUNT(action IN registration, login) | Все события включая повторные |
| Unique % | Registrations / All Leads × 100 | Доля уникальных в общем трафике |
| EPL Primary | Revenue / All Leads | Доход на одного лида |
| Sales | COUNT из keitaro (CPA + sale) | Состоявшиеся продажи |
| CR % | Sales / All Leads × 100 | Конверсия трафика в продажи |
| Revenue | SUM(revenue) из keitaro | Выручка от новых пользователей |
| Cost CPA | SUM(revenue) из affise | Затраты на привлечение |
| Profit | Revenue − Cost CPA | Прибыль по новым |
| ROMI % New User | Profit / Cost CPA × 100 | Возврат на затраты привлечения |

### Retention блок
| Метрика | Формула | Смысл |
|---|---|---|
| Retention Revenue | SUM(revenue) из keitaro (email/sms/push...) с CPA-атрибуцией | Доход от повторных коммуникаций |
| Cost Email | COUNT(email events) × тариф из email_rates | Затраты на email-рассылки |
| Cost SMS | COUNT(sms events) × тариф из sms_rates ÷ 41 | Затраты на SMS в USD |
| Retention Cost | Cost Email + Cost SMS | Суммарные затраты на retention |
| Retention Profit | Retention Revenue − Retention Cost | Прибыль от удержания |
| ROMI % Retention | Retention Profit / Retention Cost × 100 | Эффективность retention |

### Total блок
| Метрика | Формула |
|---|---|
| EPL Total | Revenue TOT / All Leads |
| Adsense Revenue | SUM(total_revenue) из GA4 (ad_impression) |
| Revenue TOT | Revenue + Retention Revenue + Adsense Revenue |
| Cost TOT | Cost CPA + Retention Cost |
| Profit TOT | Revenue TOT − Cost TOT |
| GPM % | Profit TOT / Revenue TOT × 100 |
| ROMI % TOT | Profit TOT / Cost TOT × 100 |

---

## 6. Ключевые технические решения

**utm_source атрибуция** — для Retention Revenue, Cost Email, Cost SMS реализована логика последнего касания: для каждого события через `pd.merge_asof` находим последний utm_source в lead_params до даты события. Учитываем только `CPA, google, facebook, tiktok, bigo, bing, zalo`. В дашборд попадают только события с utm_source = CPA.

**Range join по тарифам** — тариф email/sms определяется через `merge_asof` по условию `dt_from <= дата_события < dt_to`. Для SMS дополнительно фильтруем по стране.

**Фильтрация keitaro** — применяются фильтры по `ts` и `campaign_group` согласно стране (например, mx → Broker MX / Finance MX). Строки с `campaign_group="Other"` и `revenue=999` исключены как шум.

**Конвертация UAH→USD** — фиксированный курс 1 USD = 41 UAH (допущение, см. раздел 8).

---

## 7. Результат

Финальный датасет `output/dashboard_final.csv`:
- **18 строк** — по одной на каждого уникального партнёра
- **26 колонок** — все метрики из ТЗ + `network_id` для иерархического фильтра
- Визуализация реализована в **Looker Studio** с фильтрами по Country, Partner ID (network_id), Affid (partner_id)

---

## 8. Открытые вопросы и допущения

| # | Вопрос | Допущение |
|---|---|---|
| 1 | Курс UAH→USD для SMS не указан в ТЗ | Фиксированный курс 1 USD = 41 UAH |
| 2 | Какую дату брать для lookup тарифа email/sms | Дата события из scenario_log |
| 3 | Что делать с пустыми aff_id в GA4 | Исключаем строки с `(not set)` |
| 4 | 6 лидов с affid=NaN (utm_source=google) | Исключены из CPA-дашборда |
| 5 | Тариф email/sms — за одну отправку или за 1000 | Интерпретируем как за одну отправку |
| 6 | Retention Revenue только CPA-атрибуция | google/facebook трафик не включается |

---

## 9. Известные ограничения

**Date-фильтр** — дашборд не поддерживает корректную фильтрацию по дате. Причина архитектурная: лиды, продажи и затраты записываются в разных источниках на разные даты (лид приходит сегодня, конвертируется через недели). Агрегировать их в одну строку с единой датой невозможно без потери корректности метрик.

В продакшне это решается через BigQuery с date-партиционированием: каждый источник фильтруется по своей нативной дате на уровне SQL-запроса, а не на уровне готовой агрегированной таблицы.

**Читаемость дашборда** — 22 метрики в одной таблице сложно читать. В продакшне рекомендуется разбить на отдельные страницы: Leads/Affiliates, Keitaro (Sales + Retention), Adsense, Overview.

---

## 10. Порядок реализации в продакшне

1. Настроить BigQuery dataset + загрузить CRM-таблицы (lead_params, scenario_log)
2. Подключить Affise API → scheduled export в BigQuery
3. Подключить Keitaro API → scheduled export в BigQuery
4. Подключить GA4 → BigQuery export (нативная интеграция)
5. Загрузить rate tables (email_rates, sms_rates) как справочники в BigQuery
6. Реализовать intermediate views по SQL из папки `sql/intermediate/`
7. Реализовать финальный mart view (`sql/mart/final_view.sql`)
8. Подключить Looker Studio к BigQuery → настроить дашборд
9. Добавить курс UAH→USD как отдельную таблицу с историческими значениями (НБУ API)
