from dataclasses import dataclass
from typing import Any, Optional
from utils.models import SeverityLevel

@dataclass
class BusinessRule:
    rule_id: str
    rule_name: str
    table_name: str
    column_name: str
    rule_description: str
    validation_logic: str
    severity: SeverityLevel
    column_type: Optional[str] = None      # ← NEW: 'string', 'numeric', 'date', or None
    allow_negative: bool = False
    allow_zero: bool = False
    allow_decimals: bool = False
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    allowed_values: Optional[list] = None

class BusinessRuleEngine:
    def __init__(self):
        self.rules: dict = {}
    
    def add_rule(self, rule: BusinessRule):
        self.rules[rule.rule_id] = rule
    
    def get_rule(self, rule_id: str) -> Optional[BusinessRule]:
        return self.rules.get(rule_id)
    
    def generate_validation_query(self, rule: BusinessRule, table_name: str, column_name: str) -> str:
        query = f"SELECT COUNT(*) as failure_count FROM {table_name} WHERE NOT ({rule.validation_logic})"
        return query
    
    def get_all_rules(self) -> list:
        return list(self.rules.values())