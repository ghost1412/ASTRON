from workers.lineage import LineageFactory

def test_simple_select_lineage():
    sql = "SELECT id, name FROM users"
    extractor = LineageFactory.get_extractor("postgres")
    lineage = extractor.extract(sql)
    
    assert any(l[1] == "id" for l in lineage)
    assert any(l[1] == "name" for l in lineage)

def test_where_clause_detection():
    sql = "SELECT * FROM users WHERE email = 'test@example.com'"
    extractor = LineageFactory.get_extractor("postgres")
    lineage = extractor.extract(sql)
    
    where_cols = [l for l in lineage if l[2] == "WHERE"]
    assert len(where_cols) > 0
    assert where_cols[0][1] == "email"

def test_single_table_resolution():
    sql = "SELECT id FROM orders"
    extractor = LineageFactory.get_extractor("postgres")
    lineage = extractor.extract(sql)
    assert any(l[0] == "orders" for l in lineage)

if __name__ == "__main__":
    pytest.main()
