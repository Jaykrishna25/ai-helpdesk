"""Agent 10 - Learning / Continuous Improvement.
On ticket resolution, drafts a KB candidate (status='draft') from the student
query + faculty answer, embeds it, and queues it for admin approval. Once
approved it is re-indexed and answers future students automatically."""
from .base import BaseAgent
from ..models import KnowledgeBase, Ticket
from ..rag.embeddings import embed

class LearningAgent(BaseAgent):
    name = "LearningAgent"
    def propose_from_ticket(self, db, ticket_id):
        t = db.get(Ticket, ticket_id)
        if not t or not t.faculty_answer:
            return None
        kb = KnowledgeBase(question=t.query, answer=t.faculty_answer,
                           department_id=t.department_id, status="draft",
                           embedding=embed(t.query),
                           source_url=f"resolved:{t.ticket_id}")
        db.add(kb); db.flush()
        return kb

    def approve(self, db, knowledge_id, approver_id):
        kb = db.get(KnowledgeBase, knowledge_id)
        kb.status = "approved"
        kb.approved_by = approver_id
        kb.version += 1
        kb.embedding = embed(kb.question + " " + kb.answer)  # re-index
        db.flush()
        return kb
