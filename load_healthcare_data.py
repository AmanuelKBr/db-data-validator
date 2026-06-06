"""
Load Kaggle Healthcare Dataset into SQL Server
Reads from Downloads folder, loads into dbo.PatientRecords
Run from project root: python load_healthcare_data.py
"""

import pandas as pd
from sqlalchemy import create_engine, text

CSV_PATH = r'C:\Users\betha\Downloads\archive\healthcare_dataset.csv'
SERVER   = 'BETHAMAN'
DATABASE = 'HealthcareDemo'
DRIVER   = 'ODBC Driver 17 for SQL Server'

print("Reading CSV...")
df = pd.read_csv(CSV_PATH)

# Rename columns to match schema
df.columns = [
    'Name', 'Age', 'Gender', 'BloodType', 'MedicalCondition',
    'DateOfAdmission', 'Doctor', 'Hospital', 'InsuranceProvider',
    'BillingAmount', 'RoomNumber', 'AdmissionType', 'DischargeDate',
    'Medication', 'TestResults'
]

# Convert dates
df['DateOfAdmission'] = pd.to_datetime(df['DateOfAdmission']).dt.date
df['DischargeDate']   = pd.to_datetime(df['DischargeDate']).dt.date

# Round billing to 2 decimal places
df['BillingAmount'] = df['BillingAmount'].round(2)

print(f"Loaded {len(df):,} rows from CSV. Connecting to SQL Server...")

conn_str = (
    f"mssql+pyodbc://{SERVER}/{DATABASE}"
    f"?driver={DRIVER.replace(' ', '+')}&trusted_connection=yes"
)
engine = create_engine(conn_str, fast_executemany=True)

print("Inserting into dbo.PatientRecords (this may take ~30 seconds)...")
df.to_sql(
    'PatientRecords',
    engine,
    schema='dbo',
    if_exists='append',
    index=False,
    chunksize=1000
)

# Verify
with engine.connect() as conn:
    count = conn.execute(text("SELECT COUNT(*) FROM dbo.PatientRecords")).scalar()

print(f"✅ Done! {count:,} rows loaded into dbo.PatientRecords")