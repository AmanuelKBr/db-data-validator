import json
import os
from typing import List, Dict, Any
from utils.models import SeverityLevel
from rules.business_rules import BusinessRule, BusinessRuleEngine

class RuleLoader:
    def __init__(self, config_dir: str = "rules/configs"):
        self.config_dir = config_dir
        self.engine = BusinessRuleEngine()
        self.loaded_rulesets = {}
    
    def load_ruleset(self, filename: str) -> BusinessRuleEngine:
        filepath = os.path.join(self.config_dir, filename)
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Ruleset file not found: {filepath}")
        
        with open(filepath, 'r') as f:
            config = json.load(f)
        
        self.engine = BusinessRuleEngine()
        for rule_data in config.get('rules', []):
            rule = BusinessRule(
                rule_id=rule_data['rule_id'],
                rule_name=rule_data['rule_name'],
                table_name=rule_data.get('table_name', ''),
                column_name=rule_data.get('column_name', ''),
                rule_description=rule_data['rule_description'],
                validation_logic=rule_data['validation_logic'],
                severity=SeverityLevel(rule_data.get('severity', 'WARNING')),
                column_type=rule_data.get('column_type', None),   # ← NEW
                allow_negative=rule_data.get('allow_negative', False),
                allow_zero=rule_data.get('allow_zero', False),
                allow_decimals=rule_data.get('allow_decimals', False),
                min_length=rule_data.get('min_length'),
                max_length=rule_data.get('max_length'),
                allowed_values=rule_data.get('allowed_values')
            )
            self.engine.add_rule(rule)
        
        self.loaded_rulesets[filename] = config
        return self.engine
    
    def load_multiple_rulesets(self, filenames: List[str]) -> BusinessRuleEngine:
        self.engine = BusinessRuleEngine()
        for filename in filenames:
            filepath = os.path.join(self.config_dir, filename)
            if not os.path.exists(filepath):
                raise FileNotFoundError(f"Ruleset file not found: {filepath}")
            
            with open(filepath, 'r') as f:
                config = json.load(f)
            
            for rule_data in config.get('rules', []):
                rule = BusinessRule(
                    rule_id=rule_data['rule_id'],
                    rule_name=rule_data['rule_name'],
                    table_name=rule_data.get('table_name', ''),
                    column_name=rule_data.get('column_name', ''),
                    rule_description=rule_data['rule_description'],
                    validation_logic=rule_data['validation_logic'],
                    severity=SeverityLevel(rule_data.get('severity', 'WARNING')),
                    column_type=rule_data.get('column_type', None),   # ← NEW
                    allow_negative=rule_data.get('allow_negative', False),
                    allow_zero=rule_data.get('allow_zero', False),
                    allow_decimals=rule_data.get('allow_decimals', False),
                    min_length=rule_data.get('min_length'),
                    max_length=rule_data.get('max_length'),
                    allowed_values=rule_data.get('allowed_values')
                )
                self.engine.add_rule(rule)
            
            self.loaded_rulesets[filename] = config
        
        return self.engine
    
    def get_available_rulesets(self) -> List[str]:
        if not os.path.exists(self.config_dir):
            return []
        return sorted([f for f in os.listdir(self.config_dir) if f.endswith('.json')])
    
    def get_ruleset_category(self, filename: str) -> str:
        filepath = os.path.join(self.config_dir, filename)
        if not os.path.exists(filepath):
            return ""
        with open(filepath, 'r') as f:
            config = json.load(f)
        return config.get('category', '')
    
    def suggest_rulesets_for_schema(self, schema_dict: Dict[str, str]) -> List[str]:
        suggested = set()
        for column_name, column_type in schema_dict.items():
            col_type_lower = column_type.lower()
            if any(t in col_type_lower for t in ['int', 'bigint', 'smallint', 'decimal', 'numeric', 'float', 'money']):
                suggested.add('sample_numeric_rules.json')
            if any(t in col_type_lower for t in ['varchar', 'nvarchar', 'char', 'nchar', 'text']):
                suggested.add('sample_string_rules.json')
            if any(t in col_type_lower for t in ['datetime', 'date', 'datetime2', 'datetimeoffset']):
                suggested.add('sample_date_rules.json')
        return sorted(list(suggested))
    
    def get_engine(self) -> BusinessRuleEngine:
        return self.engine