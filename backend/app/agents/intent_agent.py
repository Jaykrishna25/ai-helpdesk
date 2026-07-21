"""Agent 1 - Intent Recognition.
Production: fine-tuned DistilBERT sequence classifier (15 intents).
Demo: normalized-text keyword/pattern scorer with softmax-like confidence.
"""
import re
from .base import BaseAgent, AgentContext

# Query normalization (tokenize -> expand abbreviations -> lemmatize-lite)
ABBREV = {"sem": "semester", "exam": "examination", "reg": "registration",
          "fee": "fees", "cert": "certificate", "hostel": "hostel",
          "info": "information", "admsn": "admission", "schol": "scholarship"}

INTENTS = {
    "ExamSchedule":     ["exam", "examination", "timetable", "exam date", "when will", "semester exam"],
    "FeeInquiry":       ["fee", "fees", "tuition", "payment", "due", "installment"],
    "AdmissionStatus":  ["admission", "apply", "application status", "merit list", "seat"],
    "LibraryIssue":     ["library", "book", "renew", "return", "fine", "borrow"],
    "HostelRequest":    ["hostel", "room", "mess", "accommodation", "warden"],
    "PlacementInquiry": ["placement", "company", "recruit", "internship", "drive", "package"],
    "ScholarshipStatus":["scholarship", "stipend", "financial aid", "waiver"],
    "AcademicCalendar": ["calendar", "holiday", "semester start", "reopen", "academic year"],
    "CertificateRequest":["certificate", "bonafide", "transcript", "marksheet", "degree"],
    "AttendanceIssue":  ["attendance", "shortage", "condonation", "present", "absent"],
    "ResultInquiry":    ["result", "grade", "cgpa", "sgpa", "revaluation", "backlog"],
    "CourseRegistration":["register course", "elective", "add drop", "course registration", "enroll"],
    "IDCardRequest":    ["id card", "identity card", "lost card", "duplicate card"],
    "GrievanceComplaint":["complaint", "grievance", "harassment", "ragging", "issue with"],
    "GeneralInfo":      ["contact", "office hours", "where is", "how to", "phone number"],
}
_ABBR_RE = re.compile(r"\b(" + "|".join(ABBREV) + r")\b")

def normalize(text: str) -> str:
    t = text.lower().strip()
    t = _ABBR_RE.sub(lambda m: ABBREV[m.group(1)], t)
    t = re.sub(r"\s+", " ", t)
    return t

class IntentRecognitionAgent(BaseAgent):
    name = "IntentRecognitionAgent"
    def run(self, ctx: AgentContext, db=None):
        ctx.normalized_query = normalize(ctx.query)
        scores = {}
        for intent, kws in INTENTS.items():
            hits = sum(1 for k in kws if k in ctx.normalized_query)
            if hits:
                scores[intent] = hits
        if not scores:
            ctx.intent, ctx.intent_conf = "Unknown", 0.0
        else:
            total = sum(scores.values())
            best = max(scores, key=scores.get)
            ctx.intent = best
            ctx.intent_conf = round(scores[best] / (total + 1) + 0.5, 3)
            ctx.intent_conf = min(ctx.intent_conf, 0.99)
        ctx.log(self.name, f"intent={ctx.intent} conf={ctx.intent_conf}")
        return ctx
