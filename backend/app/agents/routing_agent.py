"""Agent 8 - Faculty Routing. Maps intent->department, assigns least-loaded
available faculty in that department (simple load balancer)."""
from .base import BaseAgent, AgentContext
from ..models import Faculty, Department

INTENT_DEPARTMENT = {
    "ExamSchedule": "Examination Cell", "ResultInquiry": "Examination Cell",
    "FeeInquiry": "Finance & Fees", "AdmissionStatus": "Admissions",
    "LibraryIssue": "Library", "HostelRequest": "Hostel",
    "PlacementInquiry": "Placement Cell", "ScholarshipStatus": "Scholarships",
    "AcademicCalendar": "Academic Office", "CertificateRequest": "Academic Office",
    "AttendanceIssue": "Academic Office", "CourseRegistration": "Academic Office",
    "IDCardRequest": "Student Services", "GrievanceComplaint": "Student Services",
    "GeneralInfo": "Student Services", "Unknown": "Student Services",
}

class FacultyRoutingAgent(BaseAgent):
    name = "FacultyRoutingAgent"
    def resolve(self, db, intent):
        dept_name = INTENT_DEPARTMENT.get(intent, "Student Services")
        dept = db.query(Department).filter_by(department_name=dept_name).first()
        if not dept:
            dept = db.query(Department).first()
        fac = (db.query(Faculty)
               .filter_by(department_id=dept.department_id, is_available=True)
               .order_by(Faculty.open_ticket_count.asc()).first())
        return dept, fac

    def run(self, ctx: AgentContext, db=None):
        dept, fac = self.resolve(db, ctx.intent)
        ctx.department_id = dept.department_id
        ctx.entities["_routed_faculty"] = fac.faculty_id if fac else None
        ctx.log(self.name, f"dept={dept.department_name} faculty={fac.faculty_id if fac else None}")
        return ctx
