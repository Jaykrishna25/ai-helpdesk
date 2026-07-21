"""Multi-Agent Orchestrator.
Coordinates the agent pipeline for a single student query, delegating tasks and
sharing state via AgentContext (blackboard). Implements the full primary use
case: retrieve -> ground -> score -> decide -> (answer | ticket+route+notify).
"""
import datetime as dt
from .base import AgentContext
from .intent_agent import IntentRecognitionAgent
from .entity_agent import EntityExtractionAgent
from .retrieval_agent import KnowledgeRetrievalAgent
from .rag_agent import RAGResponseAgent
from .confidence_agent import ConfidenceEvaluationAgent
from .decision_agent import DecisionAgent
from .routing_agent import FacultyRoutingAgent
from .ticket_agent import TicketManagementAgent
from .notification_agent import NotificationAgent
from .security_agent import SecurityAgent
from ..models import ChatHistory, Student, Faculty

class Orchestrator:
    def __init__(self):
        self.intent = IntentRecognitionAgent()
        self.entity = EntityExtractionAgent()
        self.retrieval = KnowledgeRetrievalAgent()
        self.rag = RAGResponseAgent()
        self.confidence = ConfidenceEvaluationAgent()
        self.decision = DecisionAgent()
        self.routing = FacultyRoutingAgent()
        self.ticket = TicketManagementAgent()
        self.notify = NotificationAgent()
        self.security = SecurityAgent()

    def handle_query(self, db, student_id, session_id, query):
        ctx = AgentContext(student_id=student_id, session_id=session_id, query=query)
        # 12: security screen first
        flags = self.security.screen(query)
        if "prompt_injection" in flags:
            ctx.answer = "Your message could not be processed for security reasons."
            ctx.decision = "blocked"; ctx.confidence = 0.0
            self._save_chat(db, ctx)
            return self._result(ctx, flags)
        # 1-6: understanding + retrieval + scoring + decision
        for agent in (self.intent, self.entity, self.retrieval, self.rag,
                      self.confidence, self.decision):
            agent.run(ctx, db)

        if ctx.decision == "answer":
            self._save_chat(db, ctx, answered_by="ai")
        else:  # escalate: route -> ticket -> notify student & faculty
            self.routing.run(ctx, db)
            t = self.ticket.create(db, ctx)
            student = db.get(Student, student_id)
            self.notify.send(db, student.email, "student",
                             f"[{t.ticket_id}] We're on it",
                             f"Hi {student.name}, your question was forwarded to the "
                             f"{ '' } team. Ticket {t.ticket_id} was created and you'll "
                             f"get an email when it's answered.", ticket_id=t.ticket_id)
            if t.faculty_id:
                fac = db.get(Faculty, t.faculty_id)
                self.notify.send(db, fac.email, "faculty",
                                 f"[{t.ticket_id}] New student query",
                                 f"Student {student_id} asks: {query}", ticket_id=t.ticket_id)
            ctx.answer = (f"I couldn't answer this confidently, so I've created "
                          f"ticket {ctx.ticket_id} and routed it to the right team. "
                          f"You'll receive an email once they respond.")
            self._save_chat(db, ctx, answered_by="ticket", ticket_id=ctx.ticket_id)
        db.commit()
        return self._result(ctx, flags)

    def _save_chat(self, db, ctx, answered_by=None, ticket_id=None):
        db.add(ChatHistory(student_id=ctx.student_id, session_id=ctx.session_id,
                           message=ctx.query, response=ctx.answer, intent=ctx.intent,
                           confidence=ctx.confidence, answered_by=answered_by,
                           ticket_id=ticket_id))
        db.flush()

    def _result(self, ctx, flags):
        return {"answer": ctx.answer, "intent": ctx.intent,
                "entities": {k: v for k, v in ctx.entities.items() if not k.startswith("_")},
                "confidence": ctx.confidence, "decision": ctx.decision,
                "ticket_id": ctx.ticket_id, "security_flags": flags,
                "retrieved": [{"score": r["score"], "kb_id": r["kb"].knowledge_id,
                               "question": r["kb"].question} for r in ctx.retrieved],
                "trace": ctx.trace}

orchestrator = Orchestrator()
