import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from typing import List, Dict, Any
from urllib.parse import quote_plus
import pyodbc

class SQLServerConnector:
    """Handles SQL Server database connections and queries."""
    
    def __init__(self, server: str, database: str, username: str = "", password: str = ""):
        self.server = server
        self.database = database
        self.username = username
        self.password = password
        self.engine = None
        self.connection = None
    
    def connect(self) -> bool:
        """Establish connection to SQL Server."""
        try:
            if self.username and self.password:
                connection_string = (
                    f"mssql+pyodbc://{quote_plus(self.username)}:{quote_plus(self.password)}"
                    f"@{self.server}/{self.database}?driver=ODBC+Driver+17+for+SQL+Server"
                )
            else:
                connection_string = f"mssql+pyodbc://@{self.server}/{self.database}?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes"
            
            self.engine = create_engine(connection_string)
            self.connection = self.engine.connect()
            
            # Test connection
            self.connection.execute(text("SELECT 1"))
            print(f"Connected to {self.server}/{self.database}")
            return True
        except Exception as e:
            print(f"Connection failed: {e}")
            return False
    
    def disconnect(self):
        """Close database connection."""
        if self.connection:
            self.connection.close()
        if self.engine:
            self.engine.dispose()
    
    def execute_query(self, query: str) -> List[Dict[str, Any]]:
        """Execute a SQL query and return results as list of dictionaries."""
        try:
            if not self.connection:
                raise Exception("Not connected to database")
            
            result = self.connection.execute(text(query))
            rows = result.fetchall()
            
            # Convert rows to list of dictionaries
            if rows:
                columns = list(result.keys())
                return [dict(zip(columns, row)) for row in rows]
            return []
        except Exception as e:
            print(f"Query execution error: {e}")
            return []
    
    def get_tables(self) -> List[str]:
        """Get list of all tables in the database."""
        try:
            query = """
            SELECT TABLE_SCHEMA + '.' + TABLE_NAME as table_name
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_TYPE = 'BASE TABLE'
            ORDER BY TABLE_SCHEMA, TABLE_NAME
            """
            results = self.execute_query(query)
            return [row['table_name'] for row in results] if results else []
        except Exception as e:
            print(f"Error fetching tables: {e}")
            return []
    
    def get_database_list(self) -> List[str]:
        """Get list of all databases on the server."""
        try:
            query = "SELECT name FROM sys.databases WHERE state = 0 ORDER BY name"
            results = self.execute_query(query)
            return [row['name'] for row in results] if results else []
        except Exception as e:
            print(f"Error fetching database list: {e}")
            return []
    
    def get_table_row_count(self, table_name: str) -> int:
        """Get row count for a table. Raises on failure so callers can distinguish error from empty table."""
        if not self.connection:
            raise RuntimeError("Not connected to database")
        result = self.connection.execute(text(f"SELECT COUNT(*) as row_count FROM {table_name}"))
        row = result.fetchone()
        return row[0] if row else 0
    
    def get_table_schema(self, schema_name: str, table_name: str) -> Dict[str, str]:
        """Get column names and data types for a table."""
        try:
            if not self.connection:
                raise Exception("Not connected to database")
            query = text("""
                SELECT COLUMN_NAME, DATA_TYPE
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = :schema AND TABLE_NAME = :table
                ORDER BY ORDINAL_POSITION
            """)
            result = self.connection.execute(query, {"schema": schema_name, "table": table_name})
            rows = result.fetchall()
            columns = list(result.keys())
            schema_dict = {}
            for row in rows:
                d = dict(zip(columns, row))
                schema_dict[d['COLUMN_NAME']] = d['DATA_TYPE']
            return schema_dict
        except Exception as e:
            print(f"Error getting schema for {schema_name}.{table_name}: {e}")
            return {}