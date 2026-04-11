import sqlglot
from sqlglot import exp
from typing import List, Tuple
from core.models import LineageColumn
from core.db_manager import DatabaseManager
from sqlglot.optimizer.qualify import qualify

class BaseLineageExtractor:
    """Interface for dialect-specific extraction logic."""
    def __init__(self, dialect: str):
        self.dialect = dialect

    def extract(self, sql: str) -> List[Tuple[str, str, str]]:
        try:
            # Step 1: Basic Parse
            parsed = sqlglot.parse_one(sql, read=self.dialect)
            
            # Step 2: Full AST Qualification (Resolves aliases, CTEs, and expands Stars)
            # This is the 'Grammar-First' fix for nested queries and aliases.
            qualified = qualify(parsed)
        except Exception as e:
            # Fallback for complex expressions that qualify might miss without a full schema context
            try:
                qualified = sqlglot.parse_one(sql, read=self.dialect)
            except:
                return []
        
        return self._run_extraction(qualified)

    def _run_extraction(self, expression: exp.Expression) -> List[Tuple[str, str, str]]:
        raise NotImplementedError()

class GenericLineageExtractor(BaseLineageExtractor):
    """Smarter extractor using qualified AST traversal."""
    def _run_extraction(self, parsed: exp.Expression) -> List[Tuple[str, str, str]]:
        lineage = []
        
        # We walk the AST and specifically pull Columns that have been qualified with their source tables
        for expression in parsed.find_all(exp.Column):
            column_name = expression.name
            table_name = expression.table
            
            if not table_name:
                # Fallback: If qualification was partial, guess the only table in context
                tables_in_query = [t.name for t in parsed.find_all(exp.Table)]
                table_name = tables_in_query[0] if len(tables_in_query) == 1 else "unknown"
            
            # Deep clause detection focusing on structural context
            current = expression
            clause_type = "UNKNOWN"
            while current:
                if isinstance(current, exp.Where): clause_type = "WHERE"; break
                if isinstance(current, exp.Select): clause_type = "SELECT"
                if isinstance(current, exp.Join): clause_type = "JOIN"; break
                if isinstance(current, exp.Order): clause_type = "ORDER BY"; break
                if isinstance(current, exp.Group): clause_type = "GROUP BY"; break
                current = current.parent
            
            lineage.append((table_name, column_name, clause_type or "SELECT"))
            
        return list(set(lineage)) # Return unique (Table, Column, Clause) tuples

class PostgresLineageExtractor(GenericLineageExtractor):
    """Postgres-specific overrides."""
    pass

class LineageFactory:
    """Factory for dialect-aware processors."""
    _strategies = {
        "postgres": PostgresLineageExtractor,
    }

    @classmethod
    def get_extractor(cls, dialect: str) -> BaseLineageExtractor:
        strategy_class = cls._strategies.get(dialect.lower(), GenericLineageExtractor)
        return strategy_class(dialect)

import re

def extract_columns_from_ddl(ddl: str) -> List[str]:
    """Extract column names from CREATE TABLE DDL."""
    # Matches words at the start of a line inside a column list
    cols = re.findall(r'^\s*([a-zA-Z_][a-zA-Z0-9_]*)\s+[a-zA-Z]', ddl, re.MULTILINE)
    return [c.lower() for c in cols]

def process_lineage(tenant_id: str, query_hash: str, sql: str, dialect: str):
    """Worker task to extract and store lineage with Schema-Aware resolution."""
    from sqlmodel import select
    from core.models import CachedAsset
    
    schema_map = {} # asset_name -> list of columns
    with DatabaseManager.get_session(tenant_id) as session:
        assets = session.exec(select(CachedAsset)).all()
        for asset in assets:
            schema_map[asset.asset_name] = extract_columns_from_ddl(asset.schema_ddl)

    # 2. Extract Lineage using the Strategy-aware Factory
    extractor = LineageFactory.get_extractor(dialect)
    results = extractor.extract(sql)
    
    with DatabaseManager.get_session(tenant_id) as session:
        for table, col, clause in results:
            resolved_table = table
            
            # 3. Intelligent Resolution: 
            # If table is 'unknown', check if the column exists in exactly one synced asset
            if resolved_table == "unknown":
                candidates = [asset_name for asset_name, columns in schema_map.items() if col.lower() in columns]
                if len(candidates) == 1:
                    resolved_table = candidates[0]

            lineage_entry = LineageColumn(
                query_hash=query_hash,
                asset_name=resolved_table,
                column_name=col,
                clause_type=clause
            )
            session.add(lineage_entry)
        session.commit()
