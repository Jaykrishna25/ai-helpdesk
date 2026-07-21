"""Agent 2 - Entity Extraction.
Production: BERT-NER + rules. Demo: high-precision regex/gazetteer rules.
"""
import re
from .base import BaseAgent, AgentContext

DEPARTMENTS = {
    "computer": "Computer Engineering", "cs": "Computer Engineering",
    "it": "Information Technology", "mechanical": "Mechanical Engineering",
    "civil": "Civil Engineering", "electrical": "Electrical Engineering",
    "electronics": "Electronics & Communication",
}
MONTHS = ("january february march april may june july august september "
          "october november december").split()

class EntityExtractionAgent(BaseAgent):
    name = "EntityExtractionAgent"
    def run(self, ctx: AgentContext, db=None):
        q = ctx.normalized_query
        ent = {}
        m = re.search(r"semester\s*(\d{1,2})", q) or re.search(r"\bsem\s*(\d{1,2})", q)
        if m: ent["semester"] = int(m.group(1))
        m = re.search(r"\b(\d{2}[a-z]{2}\d{3,4})\b", q)   # 21CS7042
        if m: ent["student_id"] = m.group(1).upper()
        for k, v in DEPARTMENTS.items():
            if k in q:
                ent["department"] = v
                break
        m = re.search(r"(\d{1,2})\s*(" + "|".join(MONTHS) + r")\s*(\d{4})?", q)
        if m: ent["date"] = m.group(0).strip()
        m = re.search(r"\b20\d{2}[-/]20?\d{2}\b", q)       # academic year
        if m: ent["academic_year"] = m.group(0)
        ctx.entities = ent
        ctx.log(self.name, f"entities={ent}")
        return ctx
