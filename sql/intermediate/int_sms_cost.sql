-- int_sms_cost: стоимость SMS-коммуникаций (UAH → USD)
-- Тариф берётся из sms_rates по стране и интервалу дат
-- Курс конвертации: 1 USD = 41 UAH

WITH sms AS (
    SELECT
        sl.date,
        lp.affid    AS partner_id,
        lp.country,
        sr.cost_uah / 41.0 AS cost_usd
    FROM scenario_log AS sl
    INNER JOIN lead_params AS lp
        ON sl.subid = lp.crm_id
    INNER JOIN sms_rates AS sr
        ON  lp.country = sr.country
        AND sl.date    >= sr.dt_from
        AND sl.date    <  sr.dt_to
    WHERE sl.action = 'sms'
)

SELECT
    partner_id,
    country,
    SUM(cost_usd) AS cost_sms
FROM sms
GROUP BY partner_id, country
