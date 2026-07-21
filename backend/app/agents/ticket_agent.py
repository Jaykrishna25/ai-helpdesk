"""Agent 7 - Ticket Management. Creates/tracks/closes tickets with SLA priority."""
import datetime as dt
from sqlalchemy import func
from .base import BaseAgent, AgentContext
from ..models import Ticket, Faculty

URGENT_INTENTS = {"GrievanceComplaint", "AttendanceIssue"}

def _new_ticket_id(db):
    year = dt.datetime.utcnow().year
    n = db.query(func.count(Ticket.ticket_id)).scalar() + 1
    return f"TKT-{year}-{n:06d}"

class TicketManagementAgent(BaseAgent):
    name = "TicketManagementAgent"
    def create(self, db, ctx: AgentContext):
        tid = _new_ticket_id(db)
        priority = "high" if ctx.intent in URGENT_INTENTS else "medium"
        fac_id = ctx.entities.get("_routed_faculty")
        t = Ticket(ticket_id=tid, student_id=ctx.student_id,
                   department_id=ctx.department_id, faculty_id=fac_id,
                   query=ctx.query, intent=ctx.intent,
                   ai_draft_answer=ctx.answer or None,
                   confidence=ctx.confidence,
                   status="assigned" if fac_id else "open",
                   priority=priority,
                   assigned_at=dt.datetime.utcnow() if fac_id else None)
        db.add(t)
        if fac_id:
            fac = db.get(Faculty, fac_id)
            if fac: fac.open_ticket_count += 1
        db.flush()
        ctx.ticket_id = tid
        ctx.log(self.name, f"created ticket {tid} priority={priority}")
        return t

    def resolve(self, db, ticket_id, faculty_answer):
        t = db.get(Ticket, ticket_id)
        t.faculty_answer = faculty_answer
        t.status = "resolved"
        t.resolved_at = dt.datetime.utcnow()
        if t.faculty_id:
            fac = db.get(Faculty, t.faculty_id)
            if fac and fac.open_ticket_count > 0:
                fac.open_ticket_count -= 1
        db.flush()
        return t
