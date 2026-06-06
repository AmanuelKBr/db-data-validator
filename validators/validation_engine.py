import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db_connector import SQLServerConnector
from validators.standard_rules import StandardValidationRules
from validators.rule_mapper import RuleMapper
from rules.rule_loader import RuleLoader
from utils.models import ValidationResult, ValidationFailure, TableValidationReport, SeverityLevel
from typing import List

class ValidationEngine:
    """Core engine that orchestrates database validation with explicit rule-to-column mappings."""

    def __init__(self, db_connector: SQLServerConnector, rule_loader: RuleLoader):
        self.db = db_connector
        self.rule_loader = rule_loader
        self.standard_rules = StandardValidationRules()
        self.rule_mapper = RuleMapper()

    def set_rule_mapper(self, mapper: RuleMapper):
        self.rule_mapper = mapper

    def _format_table_name(self, table_name: str) -> tuple:
        """Parse and format table name. Returns (schema, table, formatted)."""
        if '.' in table_name:
            parts = table_name.split('.')
            schema, table = parts[0], parts[1]
        else:
            schema, table = 'dbo', table_name
        return schema, table, f"[{schema}].[{table}]"

    def _get_column_type_category(self, sql_type: str) -> str:
        sql_type_lower = sql_type.lower()
        if any(t in sql_type_lower for t in ['int', 'bigint', 'smallint', 'decimal', 'numeric', 'float', 'money']):
            return 'numeric'
        elif any(t in sql_type_lower for t in ['varchar', 'nvarchar', 'char', 'nchar', 'text']):
            return 'string'
        elif any(t in sql_type_lower for t in ['datetime', 'date', 'datetime2', 'datetimeoffset']):
            return 'date'
        return None

    def _get_failing_rows(self, table_name: str, column_name: str, validation_logic: str, limit: int = 100, severity: SeverityLevel = SeverityLevel.WARNING) -> List[ValidationFailure]:
        """Fetch sample failing rows. Capped at 100 to avoid memory bloat."""
        try:
            query = f"""
            SELECT TOP {limit}
                ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) as row_num,
                [{column_name}] as actual_value
            FROM {table_name}
            WHERE NOT ({validation_logic})
            """
            rows = self.db.execute_query(query)
            return [
                ValidationFailure(
                    row_id=row.get('row_num', 0),
                    column_name=column_name,
                    actual_value=row.get('actual_value'),
                    rule_violated=validation_logic,
                    severity=severity,
                )
                for row in rows
            ]
        except Exception as e:
            print(f"Error fetching failing rows for {table_name}.{column_name}: {e}")
            return []

    @staticmethod
    def _normalize_table_name(name: str) -> str:
        """Strip brackets and lowercase for case-insensitive name comparison."""
        return name.replace('[', '').replace(']', '').lower()

    @staticmethod
    def _is_aggregate_logic(logic: str) -> bool:
        """True if logic contains GROUP BY or HAVING — cannot be safely wrapped in CASE WHEN NOT (...)."""
        upper = logic.upper()
        return 'GROUP BY' in upper or 'HAVING' in upper

    # ── batched standard checks (one query per table) ─────────────────────────

    def _batched_standard_checks(
        self,
        formatted_name: str,
        null_cols: List[str],
        blank_cols: List[str],
        total_rows: int,
    ) -> List[ValidationResult]:
        """Run all null + blank checks in a single aggregate SELECT."""
        parts = []
        index_map = []

        for col in null_cols:
            idx = len(parts)
            parts.append(f"SUM(CASE WHEN [{col}] IS NULL THEN 1 ELSE 0 END) as c{idx}")
            index_map.append(('null', col, f"[{col}] IS NULL", "NULL_VALUES", SeverityLevel.WARNING))

        for col in blank_cols:
            idx = len(parts)
            logic = f"[{col}] = '' OR LTRIM(RTRIM([{col}])) = ''"
            parts.append(f"SUM(CASE WHEN {logic} THEN 1 ELSE 0 END) as c{idx}")
            index_map.append(('blank', col, logic, "BLANK_VALUES", SeverityLevel.WARNING))

        if not parts:
            return []

        query = f"SELECT {', '.join(parts)} FROM {formatted_name}"
        try:
            rows = self.db.execute_query(query)
            row = rows[0] if rows else {}
        except Exception as e:
            print(f"Batched standard checks failed for {formatted_name}: {e}")
            return []

        results = []
        for idx, (_, col, logic, rule_name, severity) in enumerate(index_map):
            count = row.get(f"c{idx}", 0) or 0
            if count > 0:
                pct = (count / total_rows * 100) if total_rows > 0 else 0
                failing_rows = self._get_failing_rows(formatted_name, col, logic, severity=severity)
                results.append(ValidationResult(
                    table_name=formatted_name,
                    column_name=col,
                    rule_name=rule_name,
                    severity=severity,
                    total_failures=count,
                    failure_percentage=pct,
                    failures=failing_rows,
                ))
        return results

    # ── batched business-rule checks (one query per table) ────────────────────

    def _batched_business_rule_checks(
        self,
        formatted_name: str,
        rule_checks: list,
        total_rows: int,
    ) -> List[ValidationResult]:
        """Run all business-rule COUNT checks in a single aggregate SELECT."""
        parts = [
            f"SUM(CASE WHEN NOT ({logic}) THEN 1 ELSE 0 END) as c{idx}"
            for idx, (rule, col, logic) in enumerate(rule_checks)
        ]

        query = f"SELECT {', '.join(parts)} FROM {formatted_name}"
        try:
            rows = self.db.execute_query(query)
            row = rows[0] if rows else {}
        except Exception as e:
            print(f"Batched business-rule checks failed for {formatted_name}: {e}")
            return []

        results = []
        for idx, (rule, col, logic) in enumerate(rule_checks):
            count = row.get(f"c{idx}", 0) or 0
            if count > 0:
                pct = (count / total_rows * 100) if total_rows > 0 else 0
                failing_rows = self._get_failing_rows(formatted_name, col, logic, severity=rule.severity)
                results.append(ValidationResult(
                    table_name=formatted_name,
                    column_name=col,
                    rule_name=rule.rule_id,
                    severity=rule.severity,
                    total_failures=count,
                    failure_percentage=pct,
                    failures=failing_rows,
                ))
        return results

    # ── main entry point ──────────────────────────────────────────────────────

    def validate_table(self, table_name: str, selected_columns: List[str] = None, selected_rulesets: List[str] = None) -> TableValidationReport:
        """Run all validations with EXPLICIT rule-to-column mappings only."""
        schema, table, formatted_name = self._format_table_name(table_name)
        report = TableValidationReport(table_name=table_name, total_rows_checked=0, results=[])

        total_rows = self.db.get_table_row_count(formatted_name)
        report.total_rows_checked = total_rows
        if total_rows == 0:
            return report

        schema_dict = self.db.get_table_schema(schema, table)
        columns = selected_columns if selected_columns else list(schema_dict.keys())

        if selected_rulesets:
            # Only reload if the ruleset selection has changed — avoids redundant JSON I/O in batch loops
            if set(selected_rulesets) != set(self.rule_loader.loaded_rulesets.keys()):
                self.rule_loader.load_multiple_rulesets(selected_rulesets)

        # ── Standard null / blank checks ──
        null_cols = [
            c for c in columns
            if self.rule_mapper.should_apply_rule("NULL_VALUES", c)
        ]
        blank_cols = [
            c for c in columns
            if self.rule_mapper.should_apply_rule("BLANK_VALUES", c)
            and ('varchar' in schema_dict.get(c, '').lower() or 'char' in schema_dict.get(c, '').lower())
        ]

        if null_cols or blank_cols:
            report.results.extend(
                self._batched_standard_checks(formatted_name, null_cols, blank_cols, total_rows)
            )

        # ── Business rule checks ──
        engine = self.rule_loader.get_engine()
        rule_checks = []

        for rule in engine.get_all_rules():
            mapped_columns = self.rule_mapper.get_mapped_columns(rule.rule_id)
            if not mapped_columns:
                continue

            if rule.column_name:
                # Table-specific rule — compare normalized names (JSON has no brackets)
                if (self._normalize_table_name(rule.table_name) == self._normalize_table_name(formatted_name)
                        and rule.column_name in mapped_columns):
                    rule_checks.append((rule, rule.column_name, rule.validation_logic))
            else:
                # Generic column-type rule — only apply to columns with matching SQL type
                for col in mapped_columns:
                    if col not in columns:
                        continue

                    # ── TYPE COMPATIBILITY GUARD ──────────────────────────────
                    # Skip if the rule declares a column_type that doesn't match
                    # the actual SQL type of the column. This prevents numeric rules
                    # running on string columns (and vice versa) which causes silent
                    # SQL errors and makes every validation return 0 failures.
                    if rule.column_type:
                        actual_sql_type = schema_dict.get(col, '')
                        actual_category = self._get_column_type_category(actual_sql_type)
                        if actual_category != rule.column_type:
                            continue  # type mismatch or unknown type — skip safely
                    # ─────────────────────────────────────────────────────────

                    processed = rule.validation_logic.replace('[COLUMN]', f'[{col}]')

                    # Rules with aggregate logic (GROUP BY / HAVING) cannot be wrapped
                    # in CASE WHEN NOT (...) — skip with a warning
                    if self._is_aggregate_logic(processed):
                        print(f"Skipping rule {rule.rule_id} on {col}: aggregate logic cannot be batched.")
                        continue

                    rule_checks.append((rule, col, processed))

        if rule_checks:
            report.results.extend(
                self._batched_business_rule_checks(formatted_name, rule_checks, total_rows)
            )

        return report

    # ── backward compatibility ────────────────────────────────────────────────

    def _execute_validation(self, table_name: str, column_name: str, rule_name: str, description: str, query: str, severity: SeverityLevel, validation_logic: str = "", total_rows: int = None) -> ValidationResult:
        """Execute a single validation query. Prefer batched methods for bulk runs."""
        try:
            rows = self.db.execute_query(query)
            failure_count = rows[0]['failure_count'] if rows else 0
            if total_rows is None:
                total_rows = self.db.get_table_row_count(table_name)
            failure_percentage = (failure_count / total_rows * 100) if total_rows > 0 else 0

            if failure_count > 0:
                failing_rows = self._get_failing_rows(table_name, column_name, validation_logic) if validation_logic else []
                return ValidationResult(
                    table_name=table_name,
                    column_name=column_name,
                    rule_name=rule_name,
                    severity=severity,
                    total_failures=failure_count,
                    failure_percentage=failure_percentage,
                    failures=failing_rows,
                )
        except Exception as e:
            print(f"Validation query failed for {table_name}.{column_name}: {e}")
        return None