-- int_adsense: adsense-доход из GA4

SELECT
    aff_id            AS partner_id,
    country,
    SUM(total_revenue) AS adsense_revenue
FROM ga4
WHERE event_name = 'ad_impression'
  AND aff_id != '(not set)'
GROUP BY aff_id, country
