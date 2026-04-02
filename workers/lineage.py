import sqlglot
from sqlglot import exp
from typing import List, Tuple
from core.models import LineageColumn
from core.db_manager import DatabaseManager

class BaseLineageExtractor:
    """Interface for dialect-specific extraction logic."""
    def __init__(self, dialect: str):
        self.dialect = dialect

    def extract(self, sql: str) -> List[Tuple[str, str, str]]:
        try:
            parsed = sqlglot.parse_one(sql, read=self.dialect)
        except Exception as e:
            print(f"Error parsing SQL for {self.dialect}: {e}")
            return []
        return self._run_extraction(parsed)

    def _run_extraction(self, expression: exp.Expression) -> List[Tuple[str, str, str]]:
        raise NotImplementedError()

class GenericLineageExtractor(BaseLineageExtractor):
    """Fallback extractor using standard AST traversal."""
    def _run_extraction(self, parsed: exp.Expression) -> List[Tuple[str, str, str]]:
        lineage = []
        for expression in parsed.find_all(exp.Column):
            column_name = expression.name
            table_name = expression.table or "unknown"
            
            # Auto-resolve single table
            tables_in_query = [t.name for t in parsed.find_all(exp.Table)]
            if table_name == "unknown" and len(tables_in_query) == 1:
                table_name = tables_in_query[0]
            
            # Deep clause detection
            current = expression
            clause_type = "UNKNOWN"
            while current:
                if isinstance(current, exp.Where): clause_type = "WHERE"; break
                if isinstance(current, exp.Select): clause_type = "SELECT"
                if isinstance(current, exp.Join): clause_type = "JOIN"; break
                if isinstance(current, exp.Order): clause_type = "ORDER BY"; break
                current = current.parent
            
            lineage.append((table_name, column_name, clause_type or "SELECT"))
        return lineage

class PostgresLineageExtractor(GenericLineageExtractor):
    """Postgres-specific overrides (e.g. handling search_path or schema resolution)."""
    pass

class LineageFactory:
    """Senior Design Pattern: Factory for dialect-aware processors."""
    _strategies = {
        "postgres": PostgresLineageExtractor,
    }

    @classmethod
    def get_extractor(cls, dialect: str) -> BaseLineageExtractor:
        strategy_class = cls._strategies.get(dialect.lower(), GenericLineageExtractor)
        return strategy_class(dialect)

def process_lineage(tenant_id: str, query_hash: str, sql: str, dialect: str):
    """Worker task to extract and store lineage."""
    # 1. Fetch Synced Schema (CachedAsset) to help resolve unqualified columns
    from sqlmodel import select
    from core.models import CachedAsset
    
    schema_map = {} # asset_name -> list of columns
    with DatabaseManager.get_session(tenant_id) as session:
        assets = session.exec(select(CachedAsset)).all()
        for asset in assets:
            # Simplistic parsing of DDL to get columns (In production, use a proper DDL parser)
            # For now, we assume schema_ddl is available for lookup
            schema_map[asset.asset_name] = asset.schema_ddl

    # 2. Extract Lineage using the Strategy-aware Factory
    extractor = LineageFactory.get_extractor(dialect)
    results = extractor.extract(sql)
    
    with DatabaseManager.get_session(tenant_id) as session:
        for table, col, clause in results:
            resolved_table = table
            
            # Resolve 'unknown' tables by looking up column in synced schema
            if resolved_table == "unknown":
                for asset_name, ddl in schema_map.items():
                    if col.lower() in ddl.lower():
                        resolved_table = asset_name
                        break

            lineage_entry = LineageColumn(
                query_hash=query_hash,
                asset_name=resolved_table,
                column_name=col,
                clause_type=clause
            )
            session.add(lineage_entry)
        session.commit()
