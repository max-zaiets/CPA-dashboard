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
