"""
Builds a sample commercial-pharma dataset: territories, drugs, prescribers,
and 24 months of claims data. Swap for real CMS Part D data by matching the
column layout described in schema.sql.
"""
import sqlite3
import random
import os
import numpy as np
from datetime import date, timedelta

random.seed(42)
np.random.seed(42)

DB_PATH = "../data/pharma_analytics.db"

REGIONS = {
    "Northeast": ["NY-North", "NY-South", "Boston Metro", "Philadelphia"],
    "Midwest":   ["Chicago Metro", "Detroit", "Minneapolis", "St. Louis"],
    "South":     ["Dallas", "Houston", "Atlanta", "Miami"],
    "West":      ["LA Metro", "SF Bay Area", "Seattle", "Phoenix"],
}
REPS = ["J. Carter", "M. Nguyen", "A. Patel", "S. Kim", "R. Gomez", "L. Chen",
        "T. Brooks", "D. Okafor", "E. Rossi", "K. Ivanov", "P. Suzuki", "N. Haddad",
        "B. Williams", "C. Fischer", "H. Park", "V. Silva"]

THERAPEUTIC_CLASSES = {
    "Oncology":    [("Oncovex", "trastuzumab-onc"), ("Nexolar", "palbociclumab"), ("Certavia", "olumitinib")],
    "Cardiology":  [("Cardolex", "atorvastatin-cx"), ("Vasotrim", "lisinopril-vt"), ("Pulmorix", "apixaban-px")],
    "Diabetes":    [("Glucera", "semaglutide-gl"), ("Metforlin", "metformin-ml"), ("Insulara", "insulin-glargine-ia")],
    "Respiratory": [("Breathelis", "fluticasone-bl"), ("Airovent", "albuterol-av")],
    "Immunology":  [("Immunase", "adalimumab-im"), ("Rheumatrix", "tofacitinib-rx")],
}
MANUFACTURERS = ["NovaPharm", "Aurelia Biosciences", "Meridian Tx", "Corvus Health", "Halcyon Labs"]

SPECIALTIES_BY_CLASS = {
    "Oncology": "Oncology", "Cardiology": "Cardiology", "Diabetes": "Endocrinology",
    "Respiratory": "Pulmonology", "Immunology": "Rheumatology",
}
GENERALIST_SPECIALTY = "Internal Medicine"

FIRST_NAMES = ["James","Mary","Robert","Patricia","John","Jennifer","Michael","Linda","David","Elizabeth",
               "William","Barbara","Richard","Susan","Joseph","Jessica","Thomas","Sarah","Charles","Karen",
               "Priya","Wei","Fatima","Carlos","Aisha","Hiroshi","Elena","Omar","Sofia","Raj"]
LAST_NAMES = ["Smith","Johnson","Williams","Brown","Jones","Garcia","Miller","Davis","Rodriguez","Martinez",
              "Hernandez","Lopez","Gonzalez","Wilson","Anderson","Thomas","Taylor","Moore","Jackson","Martin",
              "Patel","Kim","Chen","Nguyen","Khan","Silva","Kowalski","Ivanova","Rossi","Okafor"]

PAYER_TYPES = ["Commercial", "Medicare", "Medicaid", "Cash"]
PAYER_WEIGHTS = [0.45, 0.35, 0.15, 0.05]


def build_territories(conn):
    rows, tid = [], 1
    for region, names in REGIONS.items():
        for name in names:
            rows.append((tid, name, region, random.choice(REPS)))
            tid += 1
    conn.executemany("INSERT INTO territories VALUES (?,?,?,?)", rows)
    return [r[0] for r in rows]


def build_drugs(conn):
    rows, did = [], 1
    for cls, drug_list in THERAPEUTIC_CLASSES.items():
        for brand, generic in drug_list:
            price = round(random.uniform(35, 850), 2)
            launch = random.randint(2014, 2024)
            rows.append((did, brand, generic, cls, random.choice(MANUFACTURERS), price, launch))
            did += 1
    conn.executemany("INSERT INTO drugs VALUES (?,?,?,?,?,?,?)", rows)
    return rows  # full drug rows, we need class info later


def build_prescribers(conn, territory_ids, n=450):
    rows = []
    classes = list(THERAPEUTIC_CLASSES.keys())
    for pid in range(1, n + 1):
        name = f"Dr. {random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
        npi = f"{random.randint(1000000000, 1999999999)}"
        # 70% specialists tied to a therapeutic class, 30% generalists
        if random.random() < 0.7:
            cls = random.choice(classes)
            specialty = SPECIALTIES_BY_CLASS[cls]
        else:
            specialty = GENERALIST_SPECIALTY
        territory_id = random.choice(territory_ids)
        state = random.choice(["NY","MA","PA","IL","MI","MN","MO","TX","GA","FL","CA","WA","AZ"])
        rows.append((pid, npi, name, specialty, territory_id, state))
    conn.executemany("INSERT INTO prescribers VALUES (?,?,?,?,?,?)", rows)
    return rows


def build_claims(conn, drug_rows, prescriber_rows):
    """24 months of claims with a growth trend for newer drugs and
    specialty-aligned prescribing (cardiologists mostly prescribe cardio drugs, etc.)"""
    specialty_to_class = {v: k for k, v in SPECIALTIES_BY_CLASS.items()}
    drugs_by_class = {}
    for d in drug_rows:
        drugs_by_class.setdefault(d[3], []).append(d)

    all_drug_ids = [d[0] for d in drug_rows]

    start = date(2024, 6, 1)
    months = [start.replace(day=1) for _ in range(1)]
    month_starts = []
    y, m = start.year, start.month
    for i in range(24):
        month_starts.append(date(y, m, 1))
        m += 1
        if m > 12:
            m = 1
            y += 1

    claim_id = 1
    rows = []
    for month_idx, month_start in enumerate(month_starts):
        # mild overall growth trend + seasonality (respiratory spikes in winter)
        growth_factor = 1.0 + (month_idx * 0.015)
        month_num = month_start.month
        respiratory_boost = 1.6 if month_num in (11, 12, 1, 2) else 1.0

        for prescriber in prescriber_rows:
            pid, npi, name, specialty, territory_id, state = prescriber
            cls = specialty_to_class.get(specialty)
            # number of claims this prescriber writes this month
            base_claims = np.random.poisson(3 if cls else 1.2)
            if base_claims == 0:
                continue

            for _ in range(base_claims):
                if cls and random.random() < 0.75:
                    drug = random.choice(drugs_by_class[cls])
                else:
                    drug = drug_rows[random.choice(range(len(drug_rows)))]

                drug_id, brand, generic, dclass, manuf, price, launch_year = drug
                boost = respiratory_boost if dclass == "Respiratory" else 1.0
                recency_boost = 1.4 if launch_year >= 2022 else 1.0

                qty = max(1, int(np.random.normal(30, 8)))
                days_supply = random.choice([30, 60, 90])
                patient_count = max(1, int(qty / random.choice([30, 60, 90])) or 1)
                cost = round(qty * price * growth_factor * boost * recency_boost * random.uniform(0.9, 1.1), 2)
                payer = random.choices(PAYER_TYPES, weights=PAYER_WEIGHTS)[0]

                claim_date = (month_start + timedelta(days=random.randint(0, 27))).isoformat()

                rows.append((claim_id, pid, drug_id, claim_date, payer, qty, days_supply, patient_count, cost))
                claim_id += 1

        if len(rows) >= 5000:
            conn.executemany("INSERT INTO claims VALUES (?,?,?,?,?,?,?,?,?)", rows)
            rows = []

    if rows:
        conn.executemany("INSERT INTO claims VALUES (?,?,?,?,?,?,?,?,?)", rows)

    conn.commit()
    total = conn.execute("SELECT COUNT(*) FROM claims").fetchone()[0]
    print(f"Generated {total:,} claims.")


def main():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    with open("schema.sql") as f:
        conn.executescript(f.read())

    territory_ids = build_territories(conn)
    drug_rows = build_drugs(conn)
    prescriber_rows = build_prescribers(conn, territory_ids)
    conn.commit()
    build_claims(conn, drug_rows, prescriber_rows)

    print(f"Territories: {len(territory_ids)}")
    print(f"Drugs: {len(drug_rows)}")
    print(f"Prescribers: {len(prescriber_rows)}")
    conn.close()


if __name__ == "__main__":
    main()
