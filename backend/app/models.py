"""SQLAlchemy ORM models (portable across SQLite demo & PostgreSQL prod)."""
import datetime as dt
from sqlalchemy import (Column, String, Integer, SmallInteger, Text, Boolean,
                        Numeric, DateTime, ForeignKey, JSON)
from .database import Base

def now():
    return dt.datetime.utcnow()

class Department(Base):
    __tablename__ = "departments"
    department_id = Column(Integer, primary_key=True, autoincrement=True)
    department_name = Column(String(120), unique=True, nullable=False)
    contact_email = Column(String(160))
    sla_hours = Column(Integer, default=48)

class Student(Base):
    __tablename__ = "students"
    student_id = Column(String(20), primary_key=True)
    name = Column(String(120), nullable=False)
    email = Column(String(160), unique=True, nullable=False)
    department_id = Column(Integer, ForeignKey("departments.department_id"))
    semester = Column(SmallInteger, nullable=False)
    password_hash = Column(String(255), nullable=False)
    preferred_lang = Column(String(8), default="en")

class Faculty(Base):
    __tablename__ = "faculty"
    faculty_id = Column(String(20), primary_key=True)
    name = Column(String(120), nullable=False)
    email = Column(String(160), unique=True, nullable=False)
    department_id = Column(Integer, ForeignKey("departments.department_id"))
    role = Column(String(30), default="faculty")
    password_hash = Column(String(255), nullable=False)
    is_available = Column(Boolean, default=True)
    open_ticket_count = Column(Integer, default=0)

class KnowledgeBase(Base):
    __tablename__ = "knowledge_base"
    knowledge_id = Column(Integer, primary_key=True, autoincrement=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    department_id = Column(Integer, ForeignKey("departments.department_id"))
    source_url = Column(Text)
    status = Column(String(15), default="draft")
    version = Column(Integer, default=1)
    approved_by = Column(String(20), ForeignKey("faculty.faculty_id"))
    embedding = Column(JSON)   # list[float]; pgvector column in production
    created_at = Column(DateTime, default=now)
    updated_at = Column(DateTime, default=now)

class Ticket(Base):
    __tablename__ = "tickets"
    ticket_id = Column(String(24), primary_key=True)
    student_id = Column(String(20), ForeignKey("students.student_id"))
    department_id = Column(Integer, ForeignKey("departments.department_id"))
    faculty_id = Column(String(20), ForeignKey("faculty.faculty_id"))
    query = Column(Text, nullable=False)
    intent = Column(String(40))
    ai_draft_answer = Column(Text)
    faculty_answer = Column(Text)
    confidence = Column(Numeric(4, 3))
    status = Column(String(15), default="open")
    priority = Column(String(10), default="medium")
    created_at = Column(DateTime, default=now)
    assigned_at = Column(DateTime)
    resolved_at = Column(DateTime)

class ChatHistory(Base):
    __tablename__ = "chat_history"
    chat_id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(String(20), ForeignKey("students.student_id"))
    session_id = Column(String(40))
    message = Column(Text, nullable=False)
    response = Column(Text)
    intent = Column(String(40))
    confidence = Column(Numeric(4, 3))
    answered_by = Column(String(15))
    ticket_id = Column(String(24), ForeignKey("tickets.ticket_id"))
    created_at = Column(DateTime, default=now)

class Notification(Base):
    __tablename__ = "notifications"
    notification_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(20), nullable=False)
    user_type = Column(String(10), nullable=False)
    channel = Column(String(10), default="email")
    subject = Column(String(200))
    message = Column(Text, nullable=False)
    status = Column(String(12), default="queued")
    ticket_id = Column(String(24), ForeignKey("tickets.ticket_id"))
    created_at = Column(DateTime, default=now)
    sent_at = Column(DateTime)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    log_id = Column(Integer, primary_key=True, autoincrement=True)
    actor_id = Column(String(40))
    actor_type = Column(String(15))
    action = Column(String(80), nullable=False)
    entity = Column(String(40))
    entity_id = Column(String(40))
    detail = Column(JSON)
    ip_address = Column(String(45))
    created_at = Column(DateTime, default=now)
