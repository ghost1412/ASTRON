import sqlglot
from sqlglot import exp
from typing import List, Dict
from core.models import QuerySuggestion
from core.db_manager import DatabaseManager
from datetime import datetime

class TacticalWarden:
    """Professional SQL Anti-Pattern Detection Engine."""
    
    @staticmethod
    def audit(sql: str, dialect: str) -> Dict:
        try:
            parsed = sqlglot.parse_one(sql, read=dialect)
        except Exception as e:
            return {"error": f"Parse Error: {str(e)}"}

        findings = {
            "performance_warnings": [],
            "security_alerts": [],
            "tactical_advice": [],
            "estimated_cost_score": 1.0,
            "savings_potential_pct": 0
        }

        # 1. Wildcard Audit (I/O Optimization)
        if any(isinstance(node, exp.Star) for node in parsed.find_all(exp.Star)):
            findings["performance_warnings"].append("Wildcard Column Access (SELECT *)")
            findings["tactical_advice"].append({
                "issue": "Fetching more columns than necessary.",
                "remedy": "Explicitly list required columns to minimize I/O and memory pressure.",
                "impact": "High"
            })
            findings["estimated_cost_score"] += 0.5
            findings["savings_potential_pct"] += 20

        # 2. Tautology & Redundancy Audit
        for node in parsed.find_all(exp.EQ):
            # Check for 1=1 or 'a'='a'
            if isinstance(node.left, exp.Literal) and isinstance(node.right, exp.Literal):
                if node.left == node.right:
                    findings["security_alerts"].append("Redundant Tautology (1=1)")
                    findings["tactical_advice"].append({
                        "issue": "Static comparison found in predicate logic.",
                        "remedy": "Remove redundant 1=1 filters. These are often used as injection bypasses or cause query cache misses.",
                        "impact": "Medium"
                    })

        # 3. Index Suppression Audit (SARGability)
        for where in parsed.find_all(exp.Where):
            for func in where.find_all(exp.Function):
                findings["performance_warnings"].append("Index Suppression (Function on Filtered Column)")
                findings["tactical_advice"].append({
                    "issue": f"Function '{func.key.upper()}' used on a WHERE clause column.",
                    "remedy": "This prevents 'Index Seeks'. Recommend searching on the raw column value directly.",
                    "impact": "Critical"
                })
                findings["estimated_cost_score"] += 1.0

        # 4. Cartesian Product Risk
        for join in parsed.find_all(exp.Join):
            if not join.args.get("on") and not join.args.get("using") and not join.kind == "CROSS":
                 findings["security_alerts"].append("Implicit Cartesian Product Potential")
                 findings["tactical_advice"].append({
                    "issue": "Join without explicit criteria.",
                    "remedy": "Define ON or USING clauses to prevent accidentally cross-joining massive tables.",
                    "impact": "Critical"
                })

        # Calculate final cost score normalization
        findings["estimated_cost_score"] = round(findings["estimated_cost_score"], 2)
        
        return findings

def process_ai_suggestions(tenant_id: str, query_hash: str, sql: str):
    """Worker task to generate and store tactical suggestions."""
    with DatabaseManager.get_session(tenant_id) as session:
        # Fetch current dialect for the query context
        from core.models import Query
        query_meta = session.get(Query, query_hash)
        dialect = query_meta.dialect if query_meta else "postgres"

        # Initialize/Cleanup Rec
        suggestion_rec = session.query(QuerySuggestion).filter_by(query_hash=query_hash).first()
        if not suggestion_rec:
            suggestion_rec = QuerySuggestion(query_hash=query_hash)
        
        suggestion_rec.status = "PENDING"
        suggestion_rec.updated_at = datetime.utcnow()
        session.add(suggestion_rec)
        session.commit()
        
        try:
            results = TacticalWarden.audit(sql, dialect)
            suggestion_rec.status = "DONE"
            suggestion_rec.suggestions = results
        except Exception as e:
            suggestion_rec.status = "FAILED"
            suggestion_rec.error = str(e)
            
        suggestion_rec.updated_at = datetime.utcnow()
        session.merge(suggestion_rec)
        session.commit()
