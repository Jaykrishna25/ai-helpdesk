"""Seed departments, faculty, students, and an approved knowledge base."""
from .database import SessionLocal, engine, Base
from .models import Department, Faculty, Student, KnowledgeBase
from .auth import hash_pw
from .rag.embeddings import embed

DEPARTMENTS = ["Admissions", "Examination Cell", "Placement Cell", "Library",
               "Hostel", "Finance & Fees", "Scholarships", "Academic Office",
               "Student Services"]

KB = [
 ("When do Semester 7 examinations begin?",
  "Semester 7 end-semester examinations for 2026-27 begin on 15 November 2026. The detailed timetable is published on the Examination Cell portal two weeks prior.",
  "Examination Cell"),
 ("How do I pay my semester tuition fees?",
  "Semester fees are paid online via the Student Portal > Finance > Pay Fees using net-banking/UPI/card. The last date for Semester 7 is 30 September 2026; a late fee of Rs.500 applies thereafter.",
  "Finance & Fees"),
 ("What is the last date to apply for admission?",
  "Applications for the 2026 intake close on 31 July 2026. Apply at admissions.univ.edu with your marksheets and entrance score.",
  "Admissions"),
 ("How many books can I borrow and how do I renew them?",
  "Undergraduate students may borrow up to 4 books for 14 days. Renew online via Library > My Loans (max 2 renewals) if no one has reserved the book. Overdue fine is Rs.2/day.",
  "Library"),
 ("How do I apply for hostel accommodation?",
  "Hostel applications open on the Student Portal > Hostel each June. Allotment is merit-and-distance based; the mess fee for 2026-27 is Rs.42,000/year.",
  "Hostel"),
 ("How can I check my placement eligibility?",
  "Students with CGPA >= 6.0 and no active backlogs are eligible for campus placements. Register on the Placement Cell portal and upload your resume before the drive.",
  "Placement Cell"),
 ("What is the status of my merit scholarship?",
  "Merit scholarships are disbursed within 30 days of result declaration to students in the top 10% of their branch. Track status under Scholarships > My Applications.",
  "Scholarships"),
 ("When does the semester reopen after winter break?",
  "The odd semester reopens on 2 January 2027 as per the academic calendar. Classes for all years resume on that date.",
  "Academic Office"),
 ("How do I request a bonafide certificate?",
  "Request a bonafide/transcript under Academic Office > Certificates. It is issued within 3 working days and emailed as a signed PDF.",
  "Academic Office"),
 ("What is the minimum attendance requirement?",
  "A minimum of 75% attendance per course is required to sit for end-semester exams. Between 65-75% you may apply for condonation with valid documents.",
  "Academic Office"),
 ("How do I get a duplicate ID card?",
  "Report a lost ID card at Student Services with an FIR copy; a duplicate is issued within 5 working days for a Rs.200 fee.",
  "Student Services"),
 ("How can I apply for revaluation of my result?",
  "Apply for revaluation within 10 days of result declaration via Examination Cell > Revaluation, paying Rs.300 per paper.",
  "Examination Cell"),
]

def run():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    db = SessionLocal()
    dept_ids = {}
    for name in DEPARTMENTS:
        d = Department(department_name=name,
                       contact_email=name.lower().split()[0].replace("&","and")+"@univ.edu")
        db.add(d); db.flush(); dept_ids[name] = d.department_id
    # faculty (1-2 per dept) + one admin
    fac_seed = [("F-EXAM-01","Dr. Rao Examination","exam.rao@univ.edu","Examination Cell","hod"),
                ("F-FIN-01","Ms. Nita Finance","fin.nita@univ.edu","Finance & Fees","faculty"),
                ("F-ADM-01","Mr. Iqbal Admissions","adm.iqbal@univ.edu","Admissions","faculty"),
                ("F-LIB-01","Mrs. Devi Library","lib.devi@univ.edu","Library","faculty"),
                ("F-HOS-01","Mr. Warden Hostel","hostel.warden@univ.edu","Hostel","faculty"),
                ("F-PLC-01","Dr. Menon Placement","plc.menon@univ.edu","Placement Cell","hod"),
                ("F-SCH-01","Ms. Grace Scholar","sch.grace@univ.edu","Scholarships","faculty"),
                ("F-ACD-01","Dr. Bose Academic","acd.bose@univ.edu","Academic Office","hod"),
                ("F-SVC-01","Mr. Kumar Services","svc.kumar@univ.edu","Student Services","faculty"),
                ("ADMIN-01","System Administrator","admin@univ.edu","Student Services","admin")]
    for fid, nm, em, dept, role in fac_seed:
        db.add(Faculty(faculty_id=fid, name=nm, email=em,
                       department_id=dept_ids[dept], role=role, password_hash=hash_pw("faculty123")))
    # students
    students = [("21CS7042","Aarav Sharma","aarav@student.univ.edu","Examination Cell",7),
                ("21IT6011","Diya Patel","diya@student.univ.edu","Academic Office",6),
                ("22ME4003","Rohan Gupta","rohan@student.univ.edu","Hostel",4)]
    for sid, nm, em, dept, sem in students:
        db.add(Student(student_id=sid, name=nm, email=em,
                       department_id=dept_ids[dept], semester=sem, password_hash=hash_pw("student123")))
    for q, a, dept in KB:
        db.add(KnowledgeBase(question=q, answer=a, department_id=dept_ids[dept],
                             status="approved", approved_by="ADMIN-01",
                             source_url="univ.edu/kb", embedding=embed(q + " " + a)))
    db.commit(); db.close()
    print(f"Seeded {len(DEPARTMENTS)} departments, {len(fac_seed)} faculty, "
          f"{len(students)} students, {len(KB)} KB entries.")

if __name__ == "__main__":
    run()
