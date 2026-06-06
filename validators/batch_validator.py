import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db_connector import SQLServerConnector
from rules.rule_loader import RuleLoader
from validators.validation_engine import ValidationEngine
from validators.rule_mapper import RuleMapper
from utils.models import TableValidationReport, BatchValidationReport
from typing import List, Callable, Optional

class BatchValidator:
    """Orchestrates validation across multiple tables with progress tracking."""

    def __init__(self, db_connector: SQLServerConnector, rule_loader: RuleLoader, rule_mapper: Optional[RuleMapper] = None):
        self.db = db_connector
        self.rule_loader = rule_loader
        self.engine = ValidationEngine(db_connector, rule_loader)
        if rule_mapper is not None:
            self.engine.set_rule_mapper(rule_mapper)

    def set_rule_mapper(self, mapper: RuleMapper):
        """Set the rule mapper on the internal engine (convenience wrapper)."""
        self.engine.set_rule_mapper(mapper)
    
    def validate_multiple_tables(
        self, 
        table_names: List[str], 
        selected_rulesets: List[str] = None,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> BatchValidationReport:
        """
        Validate multiple tables sequentially.
        
        Args:
            table_names: List of tables to validate (e.g., ['HR.Employees', 'Sales.Orders'])
            selected_rulesets: List of ruleset filenames to apply
            progress_callback: Callable(current_index, total_count, table_name) for progress updates
        
        Returns:
            BatchValidationReport with aggregated results
        """
        
        batch_report = BatchValidationReport(
            tables_validated=[],
            total_tables=len(table_names),
            total_issues=0,
            table_reports=[]
        )
        
        for idx, table_name in enumerate(table_names):
            # Call progress callback if provided (for UI progress bar)
            if progress_callback:
                progress_callback(idx + 1, len(table_names), table_name)
            
            try:
                # Validate this table
                table_report = self.engine.validate_table(table_name, selected_rulesets=selected_rulesets)
                
                # Add to batch report
                batch_report.table_reports.append(table_report)
                batch_report.tables_validated.append(table_name)
                
                # Increment total issues count
                batch_report.total_issues += len(table_report.results)
                
            except Exception as e:
                print(f"Error validating table {table_name}: {e}")
                # Continue with next table even if one fails
                continue
        
        return batch_report
    
    def validate_single_table(
        self, 
        table_name: str, 
        selected_rulesets: List[str] = None
    ) -> TableValidationReport:
        """Validate a single table (convenience wrapper)."""
        return self.engine.validate_table(table_name, selected_rulesets=selected_rulesets)
    
    def get_batch_summary(self, batch_report: BatchValidationReport) -> dict:
        """Generate a summary dictionary from batch report for easy access."""
        return {
            'total_tables': batch_report.total_tables,
            'tables_validated': len(batch_report.tables_validated),
            'total_issues': batch_report.total_issues,
            'critical_count': batch_report.get_critical_count(),
            'warning_count': batch_report.get_warning_count(),
            'info_count': batch_report.get_info_count(),
            'timestamp': batch_report.report_timestamp
        }