import time
from typing import Dict
from core.models import QuerySuggestion
from core.db_manager import DatabaseManager
from datetime import datetime

class AIQueryOptimizer:
    @staticmethod
    def get_suggestions(sql: str) -> Dict:
        """
        Mock LLM optimization logic.
        Expanded to include cost estimation and savings potential.
        """
        suggestions = {
            "performance_warnings": [],
            "optimized_query": sql,
            "best_practices": [],
            "security_alerts": [],
            "maintainability_notes": [],
            "estimated_cost": 0.0,
            "savings_potential": 0.0
        }
        
        sql_upper = sql.upper()
        
        # 1. Base Cost Calculation (Simulated)
        base_cost = 0.01  # $0.01 base per call
        if "JOIN" in sql_upper: base_cost += 0.05
        if "GROUP BY" in sql_upper: base_cost += 0.02
        if "SELECT *" in sql_upper: base_cost += 0.10
        suggestions["estimated_cost"] = round(base_cost, 4)
        
        # 2. Performance Analysis
        if "SELECT *" in sql_upper:
            suggestions["performance_warnings"].append("Explicitly list columns instead of using SELECT * to reduce I/O.")
            suggestions["savings_potential"] += 0.80
        
        # 3. Security Analysis (Audit Tier)
        # Check for generic injection or anti-patterns
        if "1=1" in sql_upper or "1=0" in sql_upper:
            suggestions["security_alerts"].append("Detected potential tautology anti-pattern (1=1). Ensure query is not vulnerable to injection.")
        
        if "'" in sql and "WHERE" in sql_upper:
             suggestions["security_alerts"].append("Hardcoded string literals detected in WHERE clause. Recommend using parameterized queries.")

        # 4. Maintainability Analysis
        if "JOIN" in sql_upper and ("AS" not in sql_upper and " ON " in sql_upper):
             suggestions["maintainability_notes"].append("Recommend using explicit 'AS' aliases for joined tables to improve readability.")
             
        if "WHERE" in sql_upper:
            suggestions["best_practices"].append("Ensure columns in WHERE clause are indexed for better performance.")
            
        if "JOIN" in sql_upper:
            suggestions["best_practices"].append("Check if JOIN columns have foreign key constraints and indexes.")

        return suggestions


def process_ai_suggestions(tenant_id: str, query_hash: str, sql: str):
    """Worker task to generate and store AI suggestions."""
    with DatabaseManager.get_session(tenant_id) as session:
        # Initial status: PENDING
        suggestion_rec = QuerySuggestion(
            query_hash=query_hash,
            status="PENDING",
            updated_at=datetime.utcnow()
        )
        session.add(suggestion_rec)
        session.commit()
        
        # Perform optimization
        try:
            results = AIQueryOptimizer.get_suggestions(sql)
            suggestion_rec.status = "DONE"
            suggestion_rec.suggestions = results
        except Exception as e:
            suggestion_rec.status = "FAILED"
            suggestion_rec.error = str(e)
            
        suggestion_rec.updated_at = datetime.utcnow()
        session.merge(suggestion_rec)
        session.commit()
