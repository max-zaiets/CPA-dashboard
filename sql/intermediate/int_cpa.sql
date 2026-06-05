-- int_cpa: затраты CPA из affise

SELECT
    partner_full_id   AS partner_id,
    country,
    SUM(revenue)      AS cost_cpa
FROM affise
WHERE status = 1
GROUP BY partner_full_id, country
