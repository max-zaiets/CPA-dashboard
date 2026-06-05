-- int_sales: CPA-продажи из keitaro

SELECT
    sub_id_5          AS partner_id,
    country,
    COUNT(*)          AS sales,
    SUM(revenue)      AS revenue
FROM keitaro
WHERE sub_id_4 = 'CPA'
  AND status   = 'sale'
GROUP BY sub_id_5, country
