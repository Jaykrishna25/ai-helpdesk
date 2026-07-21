"""Agent 12 - Security. RBAC checks, PII/prompt-injection screening, audit."""
import re
from .base import BaseAgent
from ..models import AuditLog

INJECTION = re.compile(r"(ignore (previous|all) instructions|system prompt|drop table|<script)", re.I)
PII = re.compile(r"\b(\d{12}|\d{3}-\d{2}-\d{4})\b")   # aadhaar/ssn-like

ROLE_SCOPES = {
    "student": {"chat", "own_tickets", "profile"},
    "faculty": {"ticket_inbox", "respond", "kb_contribute"},
    "hod":     {"ticket_inbox", "respond", "kb_contribute", "dept_dashboard"},
    "admin":   {"user_mgmt", "kb_approve", "analytics", "audit", "ticket_inbox"},
}

class SecurityAgent(BaseAgent):
    name = "SecurityAgent"
    def screen(self, text: str):
        flags = []
        if INJECTION.search(text): flags.append("prompt_injection")
        if PII.search(text): flags.append("pii_detected")
        return flags

    def can(self, role: str, scope: str) -> bool:
        return scope in ROLE_SCOPES.get(role, set())

    def audit(self, db, actor_id, actor_type, action, entity=None,
              entity_id=None, detail=None, ip=None):
        db.add(AuditLog(actor_id=actor_id, actor_type=actor_type, action=action,
                        entity=entity, entity_id=str(entity_id) if entity_id else None,
                        detail=detail, ip_address=ip))
        db.flush()
