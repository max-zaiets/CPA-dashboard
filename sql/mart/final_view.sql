-- mart_dashboard: финальная витрина для CPA Dashboard
-- Джойн всех промежуточных таблиц по partner_id + country

WITH
leads       AS (SELECT * FROM int_leads),
sales       AS (SELECT * FROM int_sales),
ret_rev     AS (SELECT * FROM int_retention_rev),
cpa         AS (SELECT * FROM int_cpa),
email_cost  AS (SELECT * FROM int_email_cost),
sms_cost    AS (SELECT * FROM int_sms_cost),
adsense     AS (SELECT * FROM int_adsense),

joined AS (
    SELECT
        l.partner_id,
        l.country,
        l.registrations,
        l.all_leads,
        COALESCE(s.sales,               0) AS sales,
        COALESCE(s.revenue,             0) AS revenue,
        COALESCE(r.retention_revenue,   0) AS retention_revenue,
        COALESCE(c.cost_cpa,            0) AS cost_cpa,
        COALESCE(e.cost_email,          0) AS cost_email,
        COALESCE(sm.cost_sms,           0) AS cost_sms,
        COALESCE(a.adsense_revenue,     0) AS adsense_revenue
    FROM leads AS l
    LEFT JOIN sales       AS s  USING (partner_id, country)
    LEFT JOIN ret_rev     AS r  USING (partner_id, country)
    LEFT JOIN cpa         AS c  USING (partner_id, country)
    LEFT JOIN email_cost  AS e  USING (partner_id, country)
    LEFT JOIN sms_cost    AS sm USING (partner_id, country)
    LEFT JOIN adsense     AS a  USING (partner_id, country)
)

SELECT
    partner_id,
    country,

    -- Лиды
    registrations,
    all_leads                                                                               AS leads,
    SAFE_DIVIDE(registrations, all_leads) * 100                                            AS unique_pct,

    -- EPL
    SAFE_DIVIDE(revenue, all_leads)                                                        AS epl_primary,
    SAFE_DIVIDE(revenue + retention_revenue + adsense_revenue, all_leads)                  AS epl_total,

    -- Продажи
    sales,
    SAFE_DIVIDE(sales, all_leads) * 100                                                    AS cr_pct,

    -- New User P&L
    revenue,
    cost_cpa,
    revenue - cost_cpa                                                                     AS profit,
    SAFE_DIVIDE(revenue - cost_cpa, cost_cpa) * 100                                       AS romi_new_user,

    -- Retention P&L
    retention_revenue,
    cost_email,
    cost_sms,
    cost_email + cost_sms                                                                  AS retention_cost,
    retention_revenue - (cost_email + cost_sms)                                            AS retention_profit,
    SAFE_DIVIDE(retention_revenue - (cost_email + cost_sms), cost_email + cost_sms) * 100 AS romi_retention,

    -- Adsense
    adsense_revenue,

    -- Total P&L
    revenue + retention_revenue + adsense_revenue                                          AS revenue_tot,
    cost_cpa + cost_email + cost_sms                                                       AS cost_tot,
    (revenue + retention_revenue + adsense_revenue) - (cost_cpa + cost_email + cost_sms)  AS profit_tot,
    SAFE_DIVIDE(
        (revenue + retention_revenue + adsense_revenue) - (cost_cpa + cost_email + cost_sms),
        revenue + retention_revenue + adsense_revenue
    ) * 100                                                                                AS gpm_pct,
    SAFE_DIVIDE(
        (revenue + retention_revenue + adsense_revenue) - (cost_cpa + cost_email + cost_sms),
        cost_cpa + cost_email + cost_sms
    ) * 100                                                                                AS romi_tot

FROM joined
ORDER BY partner_id, country
