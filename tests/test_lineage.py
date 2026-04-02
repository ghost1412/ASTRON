import pytest
from workers.lineage import LineageExtractor

def test_lineage_extraction_postgres():
    sql = "SELECT id, name FROM users WHERE email = 'test@example.com' JOIN orders ON users.id = orders.user_id"
    lineage = LineageExtractor.extract(sql, "postgres")
    
    # Check for expected tables and columns
    # Note: Extract might return 'unknown' for tables if not fully qualified/schema provided, 
    # but sqlglot often finds them.
    cols = [c[1] for c in lineage]
    assert "id" in cols
    assert "name" in cols
    assert "email" in cols

def test_lineage_clause_types():
    sql = "SELECT name FROM users WHERE id = 1"
    lineage = LineageExtractor.extract(sql, "postgres")
    
    where_cols = [c[1] for c in lineage if c[2] == "WHERE"]
    select_cols = [c[1] for c in lineage if c[2] == "SELECT"]
    
    assert "id" in where_cols
    assert "name" in select_cols
