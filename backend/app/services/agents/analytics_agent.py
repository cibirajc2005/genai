"""Allowlisted natural-language analytics; no model-generated SQL is executed."""

from app.services.database import connection


def answer_analytics(question: str) -> dict:
    q = question.lower()
    with connection() as db:
        if "department" in q:
            rows = db.execute("SELECT department AS label, COUNT(*) AS value FROM documents GROUP BY department ORDER BY value DESC").fetchall()
            data = [dict(row) for row in rows]
            answer = f"{data[0]['label']} has the most documents ({data[0]['value']})." if data else "No documents are indexed."
            return {"answer": answer, "data": data, "visualization": "bar"}
        if "chunk" in q:
            rows = db.execute("SELECT d.name AS label, COUNT(c.id) AS value FROM documents d LEFT JOIN chunks c ON c.document_id=d.id GROUP BY d.id,d.name ORDER BY value DESC LIMIT 10").fetchall()
            return {"answer": "Documents ranked by indexed chunk count.", "data": [dict(row) for row in rows], "visualization": "bar"}
        if "response time" in q or "average" in q:
            value = db.execute("SELECT COALESCE(AVG(latency_ms),0) AS value FROM query_logs").fetchone()["value"]
            return {"answer": f"Average response time is {round(value)} ms.", "data": [{"label": "Average latency", "value": round(value)}], "visualization": "number"}
        if "successful" in q or "answered" in q:
            value = db.execute("SELECT COUNT(*) AS value FROM query_logs WHERE successful=1").fetchone()["value"]
            return {"answer": f"{value} questions were answered successfully.", "data": [{"label": "Successful answers", "value": value}], "visualization": "number"}
        if "how many" in q or "document" in q:
            value = db.execute("SELECT COUNT(*) AS value FROM documents").fetchone()["value"]
            return {"answer": f"There are {value} indexed documents.", "data": [{"label": "Documents", "value": value}], "visualization": "number"}
    return {"answer": "I can report document totals, department distribution, chunk counts, successful answers, or average response time.", "data": [], "visualization": "none"}
