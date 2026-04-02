import sqlglot
from sqlglot import exp
from typing import List, Tuple
from core.models import LineageColumn
from core.db_manager import DatabaseManager

class LineageExtractor:
    @staticmethod
    def extract(sql: str, dialect: str = "postgres") -> List[Tuple[str, str, str]]:
        """
        Extracts (table_name, column_name, clause_type) from a SQL query.
        """
        try:
            parsed = sqlglot.parse_one(sql, read=dialect)
        except Exception as e:
            print(f"Error parsing SQL: {e}")
            return []

        lineage = []
        
        # 1. Extract Tables
        # sqlglot makes it easy to find tables
        # tables = [t.name for t in parsed.find_all(exp.Table)]
        
        # 2. Extract Columns and their usage
        for expression in parsed.find_all(exp.Column):
            column_name = expression.name
            table_name = expression.table or "unknown"
            
            # Identify clause type (simplistic)
            parent = expression.parent
            clause_type = "SELECT"
            if isinstance(parent, exp.Where):
                clause_type = "WHERE"
            elif isinstance(parent, exp.Join):
                clause_type = "JOIN"
            elif isinstance(parent, exp.Order):
                clause_type = "ORDER BY"
            
            lineage.append((table_name, column_name, clause_type))
            
        return lineage

def process_lineage(tenant_id: str, query_hash: str, sql: str, dialect: str):
    """Worker task to extract and store lineage."""
    results = LineageExtractor.extract(sql, dialect)
    
    with DatabaseManager.get_session(tenant_id) as session:
        for table, col, clause in results:
            lineage_entry = LineageColumn(
                query_hash=query_hash,
                asset_name=table,
                column_name=col,
                clause_type=clause
            )
            session.add(lineage_entry)
        session.commit()
