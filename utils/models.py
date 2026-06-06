from enum import Enum
from dataclasses import dataclass, field
from typing import List, Any, Optional
from datetime import datetime

class SeverityLevel(Enum):
    CRITICAL = "CRITICAL"
    WARNING = "WARNING"
    INFO = "INFO"

@dataclass
class ValidationFailure:
    row_id: int
    column_name: str
    actual_value: Any
    rule_violated: str
    severity: SeverityLevel

@dataclass
class ValidationResult:
    table_name: str
    column_name: str
    rule_name: str
    severity: SeverityLevel
    total_failures: int
    failure_percentage: float
    failures: List[ValidationFailure] = field(default_factory=list)
    ai_recommendation: Optional[str] = None

@dataclass
class TableValidationReport:
    table_name: str
    total_rows_checked: int
    results: List[ValidationResult] = field(default_factory=list)
    report_timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

@dataclass
class BatchValidationReport:
    tables_validated: List[str]
    total_tables: int
    total_issues: int
    table_reports: List[TableValidationReport] = field(default_factory=list)
    report_timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def get_critical_count(self) -> int:
        """Get total CRITICAL issues across all tables."""
        return sum(
            sum(1 for r in report.results if r.severity.value == "CRITICAL")
            for report in self.table_reports
        )
    
    def get_warning_count(self) -> int:
        """Get total WARNING issues across all tables."""
        return sum(
            sum(1 for r in report.results if r.severity.value == "WARNING")
            for report in self.table_reports
        )
    
    def get_info_count(self) -> int:
        """Get total INFO issues across all tables."""
        return sum(
            sum(1 for r in report.results if r.severity.value == "INFO")
            for report in self.table_reports
        )