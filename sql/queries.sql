-- Query library for the commercial pharma dataset.
-- ANSI SQL — runs unchanged on SQLite or Postgres.

-- 1. MARKET SHARE BY THERAPEUTIC CLASS
-- "Which drugs are winning within their competitive class?"
SELECT
    d.therapeutic_class,
    d.brand_name,
    ROUND(SUM(c.total_cost), 2) AS total_revenue,
    SUM(c.quantity) AS total_units,
    ROUND(100.0 * SUM(c.total_cost) / SUM(SUM(c.total_cost)) OVER (PARTITION BY d.therapeutic_class), 1) AS market_share_pct
FROM claims c
JOIN drugs d ON d.drug_id = c.drug_id
GROUP BY d.therapeutic_class, d.brand_name
ORDER BY d.therapeutic_class, market_share_pct DESC;


-- 2. MONTH-OVER-MONTH GROWTH TREND (overall + by therapeutic class)
SELECT
    strftime('%Y-%m', claim_date) AS month,
    d.therapeutic_class,
    ROUND(SUM(c.total_cost), 2) AS revenue,
    SUM(c.quantity) AS units,
    COUNT(DISTINCT c.prescriber_id) AS active_prescribers
FROM claims c
JOIN drugs d ON d.drug_id = c.drug_id
GROUP BY month, d.therapeutic_class
ORDER BY month, d.therapeutic_class;


-- 3. TERRITORY PERFORMANCE (sales-rep-facing view)
SELECT
    t.region,
    t.territory_name,
    t.sales_rep,
    ROUND(SUM(c.total_cost), 2) AS territory_revenue,
    COUNT(DISTINCT c.prescriber_id) AS prescribing_hcps,
    COUNT(DISTINCT p.prescriber_id) AS total_hcps_in_territory,
    ROUND(100.0 * COUNT(DISTINCT c.prescriber_id) / COUNT(DISTINCT p.prescriber_id), 1) AS prescriber_penetration_pct
FROM territories t
JOIN prescribers p ON p.territory_id = t.territory_id
LEFT JOIN claims c ON c.prescriber_id = p.prescriber_id
GROUP BY t.region, t.territory_name, t.sales_rep
ORDER BY territory_revenue DESC;


-- 4. TOP PRESCRIBERS PER DRUG (identify key opinion leaders / high-value HCPs)
SELECT
    d.brand_name,
    p.prescriber_name,
    p.specialty,
    t.territory_name,
    SUM(c.quantity) AS total_units,
    ROUND(SUM(c.total_cost), 2) AS total_revenue,
    RANK() OVER (PARTITION BY d.drug_id ORDER BY SUM(c.total_cost) DESC) AS rank_within_drug
FROM claims c
JOIN prescribers p ON p.prescriber_id = c.prescriber_id
JOIN drugs d ON d.drug_id = c.drug_id
JOIN territories t ON t.territory_id = p.territory_id
GROUP BY d.brand_name, p.prescriber_name, p.specialty, t.territory_name, d.drug_id, p.prescriber_id
QUALIFY rank_within_drug <= 5  -- SQLite: replace QUALIFY block with a subquery (see queries_sqlite_compat.sql)
ORDER BY d.brand_name, rank_within_drug;


-- 5. PAYER MIX BREAKDOWN (commercial vs. Medicare vs. Medicaid vs. cash)
SELECT
    d.therapeutic_class,
    c.payer_type,
    ROUND(SUM(c.total_cost), 2) AS revenue,
    ROUND(100.0 * SUM(c.total_cost) / SUM(SUM(c.total_cost)) OVER (PARTITION BY d.therapeutic_class), 1) AS pct_of_class_revenue
FROM claims c
JOIN drugs d ON d.drug_id = c.drug_id
GROUP BY d.therapeutic_class, c.payer_type
ORDER BY d.therapeutic_class, revenue DESC;


-- 6. NEW-TO-BRAND MOMENTUM (recently launched drugs, growth trajectory)
SELECT
    d.brand_name,
    d.launch_year,
    strftime('%Y-%m', c.claim_date) AS month,
    SUM(c.quantity) AS units,
    ROUND(SUM(c.total_cost), 2) AS revenue
FROM claims c
JOIN drugs d ON d.drug_id = c.drug_id
WHERE d.launch_year >= 2022
GROUP BY d.brand_name, d.launch_year, month
ORDER BY d.brand_name, month;


-- 7. PRESCRIBER SPECIALTY MIX PER DRUG (is a drug being used on/off-label by specialty?)
SELECT
    d.brand_name,
    p.specialty,
    COUNT(DISTINCT p.prescriber_id) AS prescriber_count,
    SUM(c.quantity) AS total_units
FROM claims c
JOIN prescribers p ON p.prescriber_id = c.prescriber_id
JOIN drugs d ON d.drug_id = c.drug_id
GROUP BY d.brand_name, p.specialty
ORDER BY d.brand_name, total_units DESC;
