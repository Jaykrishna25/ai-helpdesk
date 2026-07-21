"""Agent 11 - Analytics. Aggregates KPIs for the admin dashboard."""
from sqlalchemy import func
from .base import BaseAgent
from ..models import Ticket, ChatHistory, KnowledgeBase

class AnalyticsAgent(BaseAgent):
    name = "AnalyticsAgent"
    def dashboard(self, db):
        total_chats = db.query(func.count(ChatHistory.chat_id)).scalar()
        ai_answered = db.query(func.count(ChatHistory.chat_id)).filter(
            ChatHistory.answered_by == "ai").scalar()
        tickets = db.query(func.count(Ticket.ticket_id)).scalar()
        open_t = db.query(func.count(Ticket.ticket_id)).filter(
            Ticket.status.in_(["open", "assigned", "answered"])).scalar()
        resolved = db.query(func.count(Ticket.ticket_id)).filter(
            Ticket.status.in_(["resolved", "closed"])).scalar()
        kb_pending = db.query(func.count(KnowledgeBase.knowledge_id)).filter(
            KnowledgeBase.status == "draft").scalar()
        deflection = round(100 * ai_answered / total_chats, 1) if total_chats else 0.0
        by_intent = dict(db.query(ChatHistory.intent, func.count()).group_by(
            ChatHistory.intent).all())
        return {"total_chats": total_chats, "ai_answered": ai_answered,
                "deflection_rate_pct": deflection, "tickets": tickets,
                "open_tickets": open_t, "resolved_tickets": resolved,
                "kb_pending_approval": kb_pending, "queries_by_intent": by_intent}
