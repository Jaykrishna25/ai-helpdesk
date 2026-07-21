"""FastAPI application - Cloud-Based Multi-Agent AI Student Help Desk.
Exposes auth, chat (multi-agent), tickets, knowledge base, and analytics APIs."""
import uuid
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .database import get_db, engine, Base
from .models import Student, Faculty, Ticket, KnowledgeBase, ChatHistory, Notification, Department
from .auth import verify_pw, make_token, current_user, require_role
from .agents.orchestrator import orchestrator
from .agents.ticket_agent import TicketManagementAgent
from .agents.learning_agent import LearningAgent
from .agents.notification_agent import NotificationAgent
from .agents.analytics_agent import AnalyticsAgent
from .agents.security_agent import SecurityAgent

app = FastAPI(title="AI Student Help Desk", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

ticket_agent = TicketManagementAgent()
learning_agent = LearningAgent()
notify_agent = NotificationAgent()
analytics_agent = AnalyticsAgent()
security_agent = SecurityAgent()

@app.on_event("startup")
def _startup():
    Base.metadata.create_all(engine)

# ---------- schemas ----------
class LoginReq(BaseModel):
    user_id: str
    password: str
    portal: str = "student"          # student | faculty
class ChatReq(BaseModel):
    message: str
    session_id: str | None = None
class RespondReq(BaseModel):
    answer: str
class ApproveReq(BaseModel):
    knowledge_id: int

# ---------- auth ----------
@app.post("/api/auth/login")
def login(body: LoginReq, db: Session = Depends(get_db)):
    if body.portal == "student":
        u = db.get(Student, body.user_id)
        if u and verify_pw(body.password, u.password_hash):
            return {"token": make_token(u.student_id, "student", "student"),
                    "name": u.name, "role": "student"}
    else:
        u = db.get(Faculty, body.user_id)
        if u and verify_pw(body.password, u.password_hash):
            return {"token": make_token(u.faculty_id, u.role, "faculty"),
                    "name": u.name, "role": u.role}
    raise HTTPException(401, "Invalid credentials")

# ---------- chat (multi-agent) ----------
@app.post("/api/chat")
def chat(body: ChatReq, user=Depends(current_user), db: Session = Depends(get_db)):
    if user["utype"] != "student":
        raise HTTPException(403, "Chat is for students")
    sid = body.session_id or str(uuid.uuid4())
    result = orchestrator.handle_query(db, user["id"], sid, body.message)
    result["session_id"] = sid
    return result

@app.get("/api/chat/history")
def chat_history(user=Depends(current_user), db: Session = Depends(get_db)):
    rows = (db.query(ChatHistory).filter_by(student_id=user["id"])
            .order_by(ChatHistory.created_at.desc()).limit(50).all())
    return [{"message": r.message, "response": r.response, "intent": r.intent,
             "confidence": float(r.confidence or 0), "answered_by": r.answered_by,
             "ticket_id": r.ticket_id, "at": r.created_at.isoformat()} for r in rows]

# ---------- tickets ----------
@app.get("/api/tickets/mine")
def my_tickets(user=Depends(current_user), db: Session = Depends(get_db)):
    q = db.query(Ticket)
    if user["utype"] == "student":
        q = q.filter_by(student_id=user["id"])
    else:
        q = q.filter_by(faculty_id=user["id"])
    return [_ticket_dict(t) for t in q.order_by(Ticket.created_at.desc()).all()]

@app.post("/api/tickets/{ticket_id}/respond")
def respond(ticket_id: str, body: RespondReq,
            user=Depends(require_role("faculty", "hod", "admin")),
            db: Session = Depends(get_db)):
    t = db.get(Ticket, ticket_id)
    if not t: raise HTTPException(404, "Ticket not found")
    ticket_agent.resolve(db, ticket_id, body.answer)
    kb = learning_agent.propose_from_ticket(db, ticket_id)   # draft KB candidate
    student = db.get(Student, t.student_id)
    notify_agent.send(db, student.email, "student", f"[{ticket_id}] Answered",
                      f"Your query has been answered:\n\n{body.answer}", ticket_id=ticket_id)
    security_agent.audit(db, user["id"], "faculty", "ticket.respond", "ticket", ticket_id)
    db.commit()
    return {"ok": True, "ticket_id": ticket_id, "kb_draft_id": kb.knowledge_id if kb else None}

# ---------- knowledge base ----------
@app.get("/api/kb/pending")
def kb_pending(user=Depends(require_role("admin")), db: Session = Depends(get_db)):
    rows = db.query(KnowledgeBase).filter_by(status="draft").all()
    return [{"knowledge_id": k.knowledge_id, "question": k.question,
             "answer": k.answer, "department_id": k.department_id,
             "source_url": k.source_url} for k in rows]

@app.post("/api/kb/approve")
def kb_approve(body: ApproveReq, user=Depends(require_role("admin")),
               db: Session = Depends(get_db)):
    kb = learning_agent.approve(db, body.knowledge_id, user["id"])  # re-indexes
    security_agent.audit(db, user["id"], "admin", "kb.approve", "kb", body.knowledge_id)
    db.commit()
    return {"ok": True, "knowledge_id": kb.knowledge_id, "status": kb.status}

@app.get("/api/kb")
def kb_list(user=Depends(current_user), db: Session = Depends(get_db)):
    rows = db.query(KnowledgeBase).order_by(KnowledgeBase.knowledge_id).all()
    return [{"knowledge_id": k.knowledge_id, "question": k.question,
             "status": k.status, "version": k.version} for k in rows]

# ---------- analytics ----------
@app.get("/api/analytics")
def analytics(user=Depends(require_role("admin", "hod")), db: Session = Depends(get_db)):
    return analytics_agent.dashboard(db)

@app.get("/api/notifications")
def notifications(user=Depends(current_user), db: Session = Depends(get_db)):
    rows = (db.query(Notification).filter_by(user_id=_email_of(db, user))
            .order_by(Notification.created_at.desc()).limit(30).all())
    return [{"subject": n.subject, "message": n.message, "status": n.status,
             "at": n.created_at.isoformat()} for n in rows]

@app.get("/api/health")
def health():
    from .rag.embeddings import backend_name
    return {"status": "ok", "embedding_backend": backend_name()}

# ---------- helpers ----------
def _ticket_dict(t: Ticket):
    return {"ticket_id": t.ticket_id, "student_id": t.student_id,
            "query": t.query, "intent": t.intent, "status": t.status,
            "priority": t.priority, "confidence": float(t.confidence or 0),
            "ai_draft_answer": t.ai_draft_answer, "faculty_answer": t.faculty_answer,
            "created_at": t.created_at.isoformat() if t.created_at else None}

def _email_of(db, user):
    if user["utype"] == "student":
        s = db.get(Student, user["id"]); return s.email if s else user["id"]
    f = db.get(Faculty, user["id"]); return f.email if f else user["id"]

# ---------- serve frontend (single-page app) ----------
import os
_FRONTEND = os.path.join(os.path.dirname(__file__), "..", "..", "frontend")
if os.path.isdir(_FRONTEND):
    app.mount("/", StaticFiles(directory=_FRONTEND, html=True), name="frontend")
