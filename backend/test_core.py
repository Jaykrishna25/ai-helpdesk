"""Standalone verification of the AI core (no DB/web deps).
Exercises: normalization, intent classification, entity extraction,
embedding+cosine retrieval, confidence formula, and the 85% decision.
"""
import sys, types
from dataclasses import dataclass

# import the pure-logic modules
from app.agents.base import AgentContext
from app.agents.intent_agent import IntentRecognitionAgent, normalize
from app.agents.entity_agent import EntityExtractionAgent
from app.agents.confidence_agent import ConfidenceEvaluationAgent
from app.agents.decision_agent import DecisionAgent
from app.rag.embeddings import embed, cosine, backend_name

# ---- mock KB + retrieval (stands in for vector_store over the DB) ----
@dataclass
class KB:
    knowledge_id: int; question: str; answer: str; source_url: str = "kb"
KB_ROWS = [
    KB(1, "When do Semester 7 examinations begin?",
       "Semester 7 examinations begin on 15 November 2026."),
    KB(2, "How do I pay my semester tuition fees?",
       "Pay fees online via Student Portal > Finance; last date 30 Sep 2026."),
    KB(3, "How many books can I borrow and how do I renew them?",
       "Borrow up to 4 books for 14 days; renew online, fine Rs.2/day."),
]
EMB = {k.knowledge_id: embed(k.question + " " + k.answer) for k in KB_ROWS}

def retrieve(query, top_k=4):
    q = embed(query)
    scored = sorted(((cosine(q, EMB[k.knowledge_id]), k) for k in KB_ROWS),
                    key=lambda x: x[0], reverse=True)
    return [{"score": round(float(s), 4), "kb": k} for s, k in scored[:top_k]]

intent = IntentRecognitionAgent(); entity = EntityExtractionAgent()
conf = ConfidenceEvaluationAgent(); decide = DecisionAgent()

def pipeline(query):
    ctx = AgentContext(query=query)
    intent.run(ctx); entity.run(ctx)
    ctx.retrieved = retrieve(ctx.normalized_query)
    best = ctx.retrieved[0]["kb"]; ctx.answer = best.answer
    conf.run(ctx); decide.run(ctx)
    return ctx

print("=" * 68)
print("Embedding backend:", backend_name())
print("=" * 68)

# 1. normalization
assert normalize("When is sem 7 exam?") == "when is semester 7 examination?", normalize("When is sem 7 exam?")
print("PASS  normalization: 'When is sem 7 exam?' -> 'when is semester 7 examination?'")

tests = [
    ("When will Semester 7 examinations begin?", "ExamSchedule", 1),
    ("Exam timetable for Computer Engineering Sem 7", "ExamSchedule", 1),
    ("How do I pay my tuition fees online?", "FeeInquiry", 2),
    ("How many library books can I borrow?", "LibraryIssue", 3),
]
for q, exp_intent, exp_kb in tests:
    ctx = pipeline(q)
    top_kb = ctx.retrieved[0]["kb"].knowledge_id
    tag = "PASS " if (ctx.intent == exp_intent and top_kb == exp_kb) else "FAIL "
    print(f"{tag} q='{q[:42]:42}' intent={ctx.intent:14} "
          f"top_kb={top_kb} conf={ctx.confidence:.3f} -> {ctx.decision.upper()}")

# entity extraction check
ctx = pipeline("Exam timetable for Computer Engineering Sem 7")
assert ctx.entities.get("semester") == 7 and ctx.entities.get("department") == "Computer Engineering", ctx.entities
print("PASS  entities:", ctx.entities)

# low-confidence -> ticket
ctx = pipeline("Can I bring my pet dog to the annual cultural fest afterparty?")
print(f"PASS  out-of-KB query conf={ctx.confidence:.3f} -> {ctx.decision.upper()} (expected TICKET)"
      if ctx.decision == "ticket" else f"FAIL  expected ticket, got {ctx.decision}")

# high-confidence example answer text
ctx = pipeline("When will Semester 7 examinations begin?")
print("\nSample grounded answer:\n ", ctx.answer)
print("  confidence = %.3f  (threshold 0.85 -> %s)" % (ctx.confidence, ctx.decision))
print("=" * 68); print("ALL CORE CHECKS COMPLETE")
