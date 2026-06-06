import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from typing import List, Dict, Any
import urllib.parse

class SQLServerConnector:
    """Handles SQL Server database connections and queries."""

    def __init__(self, server: str, database: str, username: str = "", password: str = ""):
        self.server = server
        self.database = database
        self.username = username
        self.password = password
        self.engine = None

    # ── connection ────────────────────────────────────────────────────────────

    def connect(self) -> bool:
        """Create the SQLAlchemy engine and verify connectivity."""
        try:
            if self.engine:
                self.engine.dispose()

            if self.username and self.password:
                odbc_str = (
                    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                    f"SERVER={self.server};"
                    f"DATABASE={self.database};"
                    f"UID={self.username};"
                    f"PWD={self.password};"
                    "Encrypt=yes;"
                    "TrustServerCertificate=yes;"
                )
            else:
                odbc_str = (
                    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                    f"SERVER={self.server};"
                    f"DATABASE={self.database};"
                    "Trusted_Connection=yes;"
                    "Encrypt=yes;"
                    "TrustServerCertificate=yes;"
                )

            conn_url = "mssql+pyodbc:///?odbc_connect=" + urllib.parse.quote_plus(odbc_str)
            # pool_pre_ping: verifies connections before reuse — prevents stale-connection errors
            # pool_size/max_overflow: modest pool for a single-user Streamlit app
            self.engine = create_engine(
                conn_url,
                pool_pre_ping=True,
                pool_size=3,
                max_overflow=5,
            )

            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))

            print(f"Connected to {self.server}/{self.database}")
            return True
        except Exception as e:
            print(f"Connection failed: {e}")
            return False

    def disconnect(self):
        if self.engine:
            self.engine.dispose()
            self.engine = None

    # ── query helpers ─────────────────────────────────────────────────────────

    def execute_query(self, query: str) -> List[Dict[str, Any]]:
        """Execute a SQL query and return results as a list of dicts."""
        try:
            if not self.engine:
                raise RuntimeError("Not connected to database")
            with self.engine.connect() as conn:
                result = conn.execute(text(query))
                rows = result.fetchall()
                if rows:
                    columns = list(result.keys())
                    return [dict(zip(columns, row)) for row in rows]
                return []
        except Exception as e:
            print(f"Query execution error: {e}")
            return []

    def get_tables(self) -> List[str]:
        """Return all BASE TABLE names in schema.table format."""
        try:
            if not self.engine:
                return []
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT TABLE_SCHEMA + '.' + TABLE_NAME AS table_name
                    FROM INFORMATION_SCHEMA.TABLES
                    WHERE TABLE_TYPE = 'BASE TABLE'
                    ORDER BY TABLE_SCHEMA, TABLE_NAME
                """))
                return [row[0] for row in result.fetchall()]
        except Exception as e:
            print(f"Error fetching tables: {e}")
            return []

    def get_database_list(self) -> List[str]:
        """Return all online database names on this server."""
        try:
            if not self.engine:
                return []
            with self.engine.connect() as conn:
                result = conn.execute(text(
                    "SELECT name FROM sys.databases WHERE state = 0 ORDER BY name"
                ))
                return [row[0] for row in result.fetchall()]
        except Exception as e:
            print(f"Error fetching database list: {e}")
            return []

    def get_table_row_count(self, table_name: str) -> int:
        """Get row count for a table. Raises on failure so callers can detect errors."""
        if not self.engine:
            raise RuntimeError("Not connected to database")
        with self.engine.connect() as conn:
            result = conn.execute(text(f"SELECT COUNT(*) AS row_count FROM {table_name}"))
            row = result.fetchone()
            return row[0] if row else 0

    def get_table_schema(self, schema_name: str, table_name: str) -> Dict[str, str]:
        """Return {column_name: data_type} for the given table."""
        try:
            if not self.engine:
                return {}
            with self.engine.connect() as conn:
                result = conn.execute(
                    text("""
                        SELECT COLUMN_NAME, DATA_TYPE
                        FROM INFORMATION_SCHEMA.COLUMNS
                        WHERE TABLE_SCHEMA = :schema AND TABLE_NAME = :table
                        ORDER BY ORDINAL_POSITION
                    """),
                    {"schema": schema_name, "table": table_name},
                )
                rows = result.fetchall()
                columns = list(result.keys())
                schema_dict = {}
                for row in rows:
                    d = dict(zip(columns, row))
                    schema_dict[d["COLUMN_NAME"]] = d["DATA_TYPE"]
                return schema_dict
        except Exception as e:
            print(f"Error getting schema for {schema_name}.{table_name}: {e}")
            return {}
