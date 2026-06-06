from typing import Dict, List, Tuple

class StandardValidationRules:
    @staticmethod
    def get_null_check_query(table_name: str, column_name: str) -> Tuple[str, str]:
        query = f"SELECT COUNT(*) as failure_count FROM {table_name} WHERE [{column_name}] IS NULL"
        return query, "NULL_VALUES"
    
    @staticmethod
    def get_blank_check_query(table_name: str, column_name: str) -> Tuple[str, str]:
        query = f"SELECT COUNT(*) as failure_count FROM {table_name} WHERE [{column_name}] = '' OR LTRIM(RTRIM([{column_name}])) = ''"
        return query, "BLANK_VALUES"
    
    @staticmethod
    def get_data_type_mismatch_query(table_name: str, column_name: str, expected_type: str) -> Tuple[str, str]:
        if expected_type.lower() in ['int', 'bigint', 'smallint']:
            query = f"SELECT COUNT(*) as failure_count FROM {table_name} WHERE TRY_CONVERT(INT, [{column_name}]) IS NULL AND [{column_name}] IS NOT NULL"
        elif expected_type.lower() in ['decimal', 'numeric', 'float']:
            query = f"SELECT COUNT(*) as failure_count FROM {table_name} WHERE TRY_CONVERT(FLOAT, [{column_name}]) IS NULL AND [{column_name}] IS NOT NULL"
        else:
            query = None
        return query, "DATA_TYPE_MISMATCH"
    
    @staticmethod
    def get_negative_values_query(table_name: str, column_name: str) -> Tuple[str, str]:
        query = f"SELECT COUNT(*) as failure_count FROM {table_name} WHERE [{column_name}] < 0"
        return query, "NEGATIVE_VALUES"
    
    @staticmethod
    def get_zero_values_query(table_name: str, column_name: str) -> Tuple[str, str]:
        query = f"SELECT COUNT(*) as failure_count FROM {table_name} WHERE [{column_name}] = 0"
        return query, "ZERO_VALUES"
    
    @staticmethod
    def get_duplicate_check_query(table_name: str, column_name: str) -> Tuple[str, str]:
        query = f"SELECT COUNT(*) as failure_count FROM (SELECT [{column_name}] FROM {table_name} GROUP BY [{column_name}] HAVING COUNT(*) > 1) AS dups"
        return query, "DUPLICATES"