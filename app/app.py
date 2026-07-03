"""
Commercial Pharma Analytics Dashboard
Run with:  streamlit run app.py
"""
import sqlite3
import pandas as pd
import streamlit as st
import plotly.express as px

DB_PATH = "../data/pharma_analytics.db"

st.set_page_config(page_title="Commercial Pharma Analytics", layout="wide")


@st.cache_resource
def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


@st.cache_data
def run_query(q, params=None):
    conn = get_connection()
    return pd.read_sql_query(q, conn, params=params)


conn = get_connection()

st.title("💊 Commercial Pharma Analytics")
st.caption("Sample dataset — prescribers, drugs, territories, and claims.")

# ---------- Filters ----------
classes = run_query("SELECT DISTINCT therapeutic_class FROM drugs ORDER BY 1")["therapeutic_class"].tolist()
regions = run_query("SELECT DISTINCT region FROM territories ORDER BY 1")["region"].tolist()

col_f1, col_f2 = st.columns(2)
with col_f1:
    sel_classes = st.multiselect("Therapeutic class", classes, default=classes)
with col_f2:
    sel_regions = st.multiselect("Region", regions, default=regions)

class_filter = ",".join(f"'{c}'" for c in sel_classes) or "''"
region_filter = ",".join(f"'{r}'" for r in sel_regions) or "''"

# ---------- KPI row ----------
kpi_q = f"""
SELECT
    ROUND(SUM(c.total_cost), 0) AS revenue,
    SUM(c.quantity) AS units,
    COUNT(DISTINCT c.prescriber_id) AS active_prescribers
FROM claims c
JOIN drugs d ON d.drug_id = c.drug_id
JOIN prescribers p ON p.prescriber_id = c.prescriber_id
JOIN territories t ON t.territory_id = p.territory_id
WHERE d.therapeutic_class IN ({class_filter}) AND t.region IN ({region_filter})
"""
kpis = run_query(kpi_q).iloc[0]

k1, k2, k3 = st.columns(3)
k1.metric("Total Revenue", f"${kpis['revenue']:,.0f}" if kpis['revenue'] else "$0")
k2.metric("Total Units", f"{kpis['units']:,.0f}" if kpis['units'] else "0")
k3.metric("Active Prescribers", f"{kpis['active_prescribers']:,.0f}" if kpis['active_prescribers'] else "0")

st.divider()

# ---------- Market share ----------
st.subheader("Market Share by Therapeutic Class")
market_share_q = f"""
SELECT d.therapeutic_class, d.brand_name, ROUND(SUM(c.total_cost),2) AS revenue,
    ROUND(100.0*SUM(c.total_cost)/SUM(SUM(c.total_cost)) OVER (PARTITION BY d.therapeutic_class),1) AS market_share_pct
FROM claims c
JOIN drugs d ON d.drug_id = c.drug_id
JOIN prescribers p ON p.prescriber_id = c.prescriber_id
JOIN territories t ON t.territory_id = p.territory_id
WHERE d.therapeutic_class IN ({class_filter}) AND t.region IN ({region_filter})
GROUP BY d.therapeutic_class, d.brand_name
ORDER BY d.therapeutic_class, market_share_pct DESC
"""
df_share = run_query(market_share_q)
fig1 = px.bar(df_share, x="brand_name", y="market_share_pct", color="therapeutic_class",
              text="market_share_pct", labels={"market_share_pct": "Market Share (%)", "brand_name": "Drug"})
st.plotly_chart(fig1, use_container_width=True)

# ---------- Revenue trend ----------
st.subheader("Monthly Revenue Trend by Therapeutic Class")
trend_q = f"""
SELECT strftime('%Y-%m', c.claim_date) AS month, d.therapeutic_class,
    ROUND(SUM(c.total_cost),2) AS revenue
FROM claims c
JOIN drugs d ON d.drug_id = c.drug_id
JOIN prescribers p ON p.prescriber_id = c.prescriber_id
JOIN territories t ON t.territory_id = p.territory_id
WHERE d.therapeutic_class IN ({class_filter}) AND t.region IN ({region_filter})
GROUP BY month, d.therapeutic_class
ORDER BY month
"""
df_trend = run_query(trend_q)
fig2 = px.line(df_trend, x="month", y="revenue", color="therapeutic_class", markers=True)
st.plotly_chart(fig2, use_container_width=True)

# ---------- Territory performance ----------
st.subheader("Territory Performance")
territory_q = f"""
SELECT t.region, t.territory_name, t.sales_rep,
    ROUND(SUM(c.total_cost), 2) AS territory_revenue,
    COUNT(DISTINCT c.prescriber_id) AS prescribing_hcps,
    COUNT(DISTINCT p.prescriber_id) AS total_hcps,
    ROUND(100.0 * COUNT(DISTINCT c.prescriber_id) / COUNT(DISTINCT p.prescriber_id), 1) AS penetration_pct
FROM territories t
JOIN prescribers p ON p.territory_id = t.territory_id
LEFT JOIN claims c ON c.prescriber_id = p.prescriber_id
LEFT JOIN drugs d ON d.drug_id = c.drug_id
WHERE t.region IN ({region_filter})
    AND (d.therapeutic_class IN ({class_filter}) OR d.therapeutic_class IS NULL)
GROUP BY t.region, t.territory_name, t.sales_rep
ORDER BY territory_revenue DESC
"""
df_territory = run_query(territory_q)
st.dataframe(df_territory, use_container_width=True, hide_index=True)

# ---------- Payer mix ----------
st.subheader("Payer Mix by Therapeutic Class")
payer_q = f"""
SELECT d.therapeutic_class, c.payer_type, ROUND(SUM(c.total_cost),2) AS revenue
FROM claims c
JOIN drugs d ON d.drug_id = c.drug_id
JOIN prescribers p ON p.prescriber_id = c.prescriber_id
JOIN territories t ON t.territory_id = p.territory_id
WHERE d.therapeutic_class IN ({class_filter}) AND t.region IN ({region_filter})
GROUP BY d.therapeutic_class, c.payer_type
"""
df_payer = run_query(payer_q)
fig3 = px.bar(df_payer, x="therapeutic_class", y="revenue", color="payer_type", barmode="stack")
st.plotly_chart(fig3, use_container_width=True)

st.divider()
st.subheader("Top 5 Prescribers per Drug")
top_prescribers_q = f"""
SELECT * FROM (
    SELECT d.brand_name, p.prescriber_name, p.specialty, t.territory_name,
        SUM(c.quantity) AS total_units, ROUND(SUM(c.total_cost),2) AS total_revenue,
        RANK() OVER (PARTITION BY d.drug_id ORDER BY SUM(c.total_cost) DESC) AS rank_within_drug
    FROM claims c
    JOIN prescribers p ON p.prescriber_id = c.prescriber_id
    JOIN drugs d ON d.drug_id = c.drug_id
    JOIN territories t ON t.territory_id = p.territory_id
    WHERE d.therapeutic_class IN ({class_filter}) AND t.region IN ({region_filter})
    GROUP BY d.brand_name, p.prescriber_name, p.specialty, t.territory_name, d.drug_id, p.prescriber_id
)
WHERE rank_within_drug <= 5
ORDER BY brand_name, rank_within_drug
"""
df_top = run_query(top_prescribers_q)
st.dataframe(df_top, use_container_width=True, hide_index=True)
