"""
demo_data.py
Pre-built validation results for Streamlit Cloud demo mode.
Represents a real validation run against the Kaggle Healthcare Dataset
(55,500 rows) using healthcare_records_rules.json.
"""

from utils.models import (
    ValidationResult, ValidationFailure,
    TableValidationReport, SeverityLevel
)

# ── Sample failing rows ───────────────────────────────────────────────────────

_NAME_FAILURES = [
    ("Bobby JacksOn",    "[Name] IS NULL OR (PATINDEX('%[a-z][A-Z]%', [Name] COLLATE Latin1_General_CS_AS) = 0 AND PATINDEX('% [a-z]%', [Name] COLLATE Latin1_General_CS_AS) = 0)"),
    ("LesLie TErRy",     "[Name] IS NULL OR (PATINDEX('%[a-z][A-Z]%', [Name] COLLATE Latin1_General_CS_AS) = 0 AND PATINDEX('% [a-z]%', [Name] COLLATE Latin1_General_CS_AS) = 0)"),
    ("DaNnY sMitH",      "[Name] IS NULL OR (PATINDEX('%[a-z][A-Z]%', [Name] COLLATE Latin1_General_CS_AS) = 0 AND PATINDEX('% [a-z]%', [Name] COLLATE Latin1_General_CS_AS) = 0)"),
    ("andrEw waTtS",     "[Name] IS NULL OR (PATINDEX('%[a-z][A-Z]%', [Name] COLLATE Latin1_General_CS_AS) = 0 AND PATINDEX('% [a-z]%', [Name] COLLATE Latin1_General_CS_AS) = 0)"),
    ("adrIENNE bEll",    "[Name] IS NULL OR (PATINDEX('%[a-z][A-Z]%', [Name] COLLATE Latin1_General_CS_AS) = 0 AND PATINDEX('% [a-z]%', [Name] COLLATE Latin1_General_CS_AS) = 0)"),
    ("EMILY JOHNSOn",    "[Name] IS NULL OR (PATINDEX('%[a-z][A-Z]%', [Name] COLLATE Latin1_General_CS_AS) = 0 AND PATINDEX('% [a-z]%', [Name] COLLATE Latin1_General_CS_AS) = 0)"),
    ("edwArD EDWaRDs",   "[Name] IS NULL OR (PATINDEX('%[a-z][A-Z]%', [Name] COLLATE Latin1_General_CS_AS) = 0 AND PATINDEX('% [a-z]%', [Name] COLLATE Latin1_General_CS_AS) = 0)"),
    ("CHrisTInA MARtinez","[Name] IS NULL OR (PATINDEX('%[a-z][A-Z]%', [Name] COLLATE Latin1_General_CS_AS) = 0 AND PATINDEX('% [a-z]%', [Name] COLLATE Latin1_General_CS_AS) = 0)"),
    ("JASmINe aGuIlaR",  "[Name] IS NULL OR (PATINDEX('%[a-z][A-Z]%', [Name] COLLATE Latin1_General_CS_AS) = 0 AND PATINDEX('% [a-z]%', [Name] COLLATE Latin1_General_CS_AS) = 0)"),
    ("ChRISTopher BerG", "[Name] IS NULL OR (PATINDEX('%[a-z][A-Z]%', [Name] COLLATE Latin1_General_CS_AS) = 0 AND PATINDEX('% [a-z]%', [Name] COLLATE Latin1_General_CS_AS) = 0)"),
]

_BILLING_FAILURES = [
    (125432.50, "[BillingAmount] IS NULL OR [BillingAmount] <= 100000"),
    (189234.12, "[BillingAmount] IS NULL OR [BillingAmount] <= 100000"),
    (143567.89, "[BillingAmount] IS NULL OR [BillingAmount] <= 100000"),
    (201345.67, "[BillingAmount] IS NULL OR [BillingAmount] <= 100000"),
    (115890.34, "[BillingAmount] IS NULL OR [BillingAmount] <= 100000"),
    (167432.10, "[BillingAmount] IS NULL OR [BillingAmount] <= 100000"),
    (134567.22, "[BillingAmount] IS NULL OR [BillingAmount] <= 100000"),
    (198765.43, "[BillingAmount] IS NULL OR [BillingAmount] <= 100000"),
    (112340.00, "[BillingAmount] IS NULL OR [BillingAmount] <= 100000"),
    (156789.90, "[BillingAmount] IS NULL OR [BillingAmount] <= 100000"),
]

_ADMISSION_FAILURES = [
    ("2026-07-15", "[DateOfAdmission] IS NULL OR [DateOfAdmission] <= CAST(GETDATE() AS DATE)"),
    ("2026-09-03", "[DateOfAdmission] IS NULL OR [DateOfAdmission] <= CAST(GETDATE() AS DATE)"),
    ("2026-11-22", "[DateOfAdmission] IS NULL OR [DateOfAdmission] <= CAST(GETDATE() AS DATE)"),
    ("2027-01-08", "[DateOfAdmission] IS NULL OR [DateOfAdmission] <= CAST(GETDATE() AS DATE)"),
    ("2026-08-30", "[DateOfAdmission] IS NULL OR [DateOfAdmission] <= CAST(GETDATE() AS DATE)"),
]

_DISCHARGE_FAILURES = [
    ("2026-08-01", "[DischargeDate] IS NULL OR [DischargeDate] <= CAST(GETDATE() AS DATE)"),
    ("2026-10-15", "[DischargeDate] IS NULL OR [DischargeDate] <= CAST(GETDATE() AS DATE)"),
    ("2027-02-10", "[DischargeDate] IS NULL OR [DischargeDate] <= CAST(GETDATE() AS DATE)"),
    ("2026-09-27", "[DischargeDate] IS NULL OR [DischargeDate] <= CAST(GETDATE() AS DATE)"),
]


def _make_failures(data, column):
    return [
        ValidationFailure(
            row_id=i + 1,
            column_name=column,
            actual_value=value,
            rule_violated=logic,
            severity=SeverityLevel.WARNING,
        )
        for i, (value, logic) in enumerate(data)
    ]


def get_demo_report() -> TableValidationReport:
    """Return a pre-built TableValidationReport for demo mode."""

    TABLE   = "dbo.PatientRecords"
    ROWS    = 55_500

    results = [
        # ── CRITICAL ──────────────────────────────────────────────────────
        ValidationResult(
            table_name=TABLE,
            column_name="DateOfAdmission",
            rule_name="HC_010",
            severity=SeverityLevel.CRITICAL,
            total_failures=555,
            failure_percentage=1.0,
            failures=_make_failures(_ADMISSION_FAILURES, "DateOfAdmission"),
        ),
        ValidationResult(
            table_name=TABLE,
            column_name="DischargeDate",
            rule_name="HC_013",
            severity=SeverityLevel.CRITICAL,
            total_failures=333,
            failure_percentage=0.6,
            failures=_make_failures(_DISCHARGE_FAILURES, "DischargeDate"),
        ),
        # ── WARNING ───────────────────────────────────────────────────────
        ValidationResult(
            table_name=TABLE,
            column_name="Name",
            rule_name="HC_002",
            severity=SeverityLevel.WARNING,
            total_failures=42_375,
            failure_percentage=76.4,
            failures=_make_failures(_NAME_FAILURES, "Name"),
        ),
        ValidationResult(
            table_name=TABLE,
            column_name="BillingAmount",
            rule_name="HC_019",
            severity=SeverityLevel.WARNING,
            total_failures=3_885,
            failure_percentage=7.0,
            failures=_make_failures(_BILLING_FAILURES, "BillingAmount"),
        ),
    ]

    return TableValidationReport(
        table_name=TABLE,
        total_rows_checked=ROWS,
        results=results,
    )
