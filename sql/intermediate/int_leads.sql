-- int_leads: регистрации и логины по partner_id + country

SELECT
    affid                                              AS partner_id,
    country,
    COUNTIF(action = 'registration')                  AS registrations,
    COUNT(*)                                           AS all_leads
FROM lead_params
WHERE action IN ('registration', 'login')
GROUP BY affid, country
