import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Dict, List, Tuple
from utils.models import SeverityLevel

class RuleMapper:
    """Manages explicit rule-to-column mappings to prevent semantic mismatches."""
    
    def __init__(self):
        self.mappings: Dict[str, List[str]] = {}  # {rule_id: [column_names]}
    
    def add_mapping(self, rule_id: str, column_names: List[str]):
        """Map a rule to specific columns."""
        self.mappings[rule_id] = column_names
    
    def remove_mapping(self, rule_id: str):
        """Remove a rule mapping."""
        if rule_id in self.mappings:
            del self.mappings[rule_id]
    
    def get_mapped_columns(self, rule_id: str) -> List[str]:
        """Get columns this rule applies to."""
        return self.mappings.get(rule_id, [])
    
    def should_apply_rule(self, rule_id: str, column_name: str) -> bool:
        """Check if a rule should apply to a specific column."""
        return column_name in self.mappings.get(rule_id, [])
    
    def get_all_mappings(self) -> Dict[str, List[str]]:
        """Get all mappings."""
        return self.mappings.copy()
    
    def clear_mappings(self):
        """Clear all mappings."""
        self.mappings.clear()
    
    def validate_mapping(self, rule_id: str, available_columns: List[str]) -> Tuple[bool, str]:
        """
        Validate that mapped columns exist in the table.
        Returns (is_valid, error_message)
        """
        mapped_columns = self.mappings.get(rule_id, [])
        
        if not mapped_columns:
            return False, f"Rule {rule_id} has no columns mapped"
        
        invalid_columns = [col for col in mapped_columns if col not in available_columns]
        
        if invalid_columns:
            return False, f"Columns {invalid_columns} do not exist in table"
        
        return True, ""