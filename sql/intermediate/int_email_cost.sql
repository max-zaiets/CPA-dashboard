-- int_email_cost: стоимость email-коммуникаций
-- Тариф берётся из email_rates по интервалу дат события

WITH emails AS (
    SELECT
        sl.date,
        lp.affid    AS partner_id,
        lp.country,
        er.cost_usd
    FROM scenario_log AS sl
    INNER JOIN lead_params AS lp
        ON sl.subid = lp.crm_id
    INNER JOIN email_rates AS er
        ON sl.date >= er.dt_from
       AND sl.date <  er.dt_to
    WHERE sl.action = 'email'
)

SELECT
    partner_id,
    country,
    SUM(cost_usd) AS cost_email
FROM emails
GROUP BY partner_id, country
