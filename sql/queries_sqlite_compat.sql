-- SQLite doesn't support QUALIFY (Postgres/Snowflake do) — same result via subquery.
SELECT * FROM (
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
)
WHERE rank_within_drug <= 5
ORDER BY brand_name, rank_within_drug;
