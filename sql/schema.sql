-- territories, drugs, prescribers, and claims (the fact table)

CREATE TABLE territories (
    territory_id    INTEGER PRIMARY KEY,
    territory_name  TEXT NOT NULL,
    region          TEXT NOT NULL,        -- Northeast, Midwest, South, West
    sales_rep       TEXT NOT NULL
);

CREATE TABLE drugs (
    drug_id             INTEGER PRIMARY KEY,
    brand_name          TEXT NOT NULL,
    generic_name        TEXT NOT NULL,
    therapeutic_class   TEXT NOT NULL,     -- e.g. Oncology, Cardiology, Diabetes
    manufacturer        TEXT NOT NULL,
    list_price_per_unit REAL NOT NULL,
    launch_year         INTEGER NOT NULL
);

CREATE TABLE prescribers (
    prescriber_id   INTEGER PRIMARY KEY,
    npi             TEXT NOT NULL UNIQUE,  -- National Provider Identifier (mock)
    prescriber_name TEXT NOT NULL,
    specialty       TEXT NOT NULL,
    territory_id    INTEGER NOT NULL REFERENCES territories(territory_id),
    state           TEXT NOT NULL
);

CREATE TABLE claims (
    claim_id        INTEGER PRIMARY KEY,
    prescriber_id   INTEGER NOT NULL REFERENCES prescribers(prescriber_id),
    drug_id         INTEGER NOT NULL REFERENCES drugs(drug_id),
    claim_date      TEXT NOT NULL,         -- YYYY-MM-DD
    payer_type      TEXT NOT NULL,         -- Commercial, Medicare, Medicaid, Cash
    quantity        INTEGER NOT NULL,
    days_supply     INTEGER NOT NULL,
    patient_count   INTEGER NOT NULL,
    total_cost      REAL NOT NULL
);

CREATE INDEX idx_claims_date ON claims(claim_date);
CREATE INDEX idx_claims_drug ON claims(drug_id);
CREATE INDEX idx_claims_prescriber ON claims(prescriber_id);
CREATE INDEX idx_prescribers_territory ON prescribers(territory_id);
