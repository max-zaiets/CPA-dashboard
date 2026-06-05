-- int_retention_rev: retention-доход из keitaro
-- sub_id_5 пустой для retention-строк → partner_id берём через sub_id_7 = crm_id

SELECT
    lp.affid          AS partner_id,
    k.country,
    SUM(k.revenue)    AS retention_revenue
FROM keitaro AS k
INNER JOIN lead_params AS lp
    ON k.sub_id_7 = lp.crm_id
WHERE k.sub_id_4 IN ('email', 'sms', 'push', 'trafficback', 'push-pwa')
  AND k.status = 'sale'
GROUP BY lp.affid, k.country
