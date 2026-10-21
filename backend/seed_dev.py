"""Idempotent dev seed: portfolio content + Thimi Tech OS Phase 1 demo org. Run: python seed_dev.py"""
import os, django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from apps.services.models import Service
from apps.projects.models import Project
from apps.team.models import TeamMember, SocialMedia
from apps.jobs.models import Job, Requirement

SERVICES = [
    ("GeoPortal Solutions", "Interactive geospatial platforms for managing and visualizing spatial information."),
    ("Municipal Management Systems", "Digital systems that support municipalities and improve information management."),
    ("AI & Machine Learning", "AI-driven solutions for automation, analysis, and intelligent decision-making."),
    ("Data Management", "Efficient systems for storing, managing, analyzing, and visualizing data."),
    ("Web & App Development", "Modern web and application solutions tailored to organizational needs."),
    ("Interactive Dashboards", "Interactive dashboards that turn complex data into useful insights."),
]
for title, desc in SERVICES:
    Service.objects.get_or_create(title=title, defaults={"description": desc})

PROJECTS = [
    ("Explore Nepal", "Travel & Culture Platform", "A dynamic platform showcasing Nepal's culture, destinations, and travel tools — combining design, data, and storytelling."),
    ("Custom Chatbot Service", "AI Assistant Platform", "Custom chatbot service with a custom knowledge base that clients can train to provide intelligent, context-aware responses tailored to their specific needs."),
    ("Geospatial Data Center", "Data Management and Geospatial Visualizations", "A centralized platform offering comprehensive spatial data, interactive mapping tools, and intelligent visualizations for planners, researchers, educators, and government bodies."),
    ("Municipal Management System", "Government Management Platform", "A geo-based system developed for municipalities to assign and manage house numbers efficiently and accurately."),
]
for name, subtitle, desc in PROJECTS:
    Project.objects.get_or_create(name=name, defaults={"subtitle": subtitle, "description": desc})

TEAM = [
    ("Ravi Shrestha", "Founder & CEO", "RS", "ravi@thimitech.com", 1),
    ("Prateek Sharma", "Lead Engineer", "PS", "", 2),
    ("Aayush Thapa", "Geospatial Developer", "AT", "", 3),
]
for name, role, initials, email, order in TEAM:
    TeamMember.objects.get_or_create(name=name, defaults={
        "role": role, "initials": initials, "email": email,
        "is_active": True, "display_order": order,
    })

JOBS = [
    ("Full-Stack Developer (Vue + Django)", "Full-time",
     "Build and maintain geospatial and AI-driven web platforms end to end.",
     ["2+ years with Vue 3 and Django REST Framework", "Comfortable with PostgreSQL/PostGIS", "Good communication in English & Nepali"]),
    ("GIS Analyst", "Full-time",
     "Work with spatial data, build maps and visualizations for municipal clients.",
     ["Experience with QGIS/PostGIS", "Python scripting a plus", "Attention to detail"]),
]
for title, etype, desc, reqs in JOBS:
    job, _ = Job.objects.get_or_create(title=title, defaults={
        "employment_type": etype, "description": desc, "is_active": True,
    })
    for i, text in enumerate(reqs):
        Requirement.objects.get_or_create(job=job, text=text, defaults={"display_order": i})

print("Seeded:",
      Service.objects.count(), "services,",
      Project.objects.count(), "projects,",
      TeamMember.objects.count(), "team,",
      Job.objects.count(), "jobs")


# ───────────────────────── Thimi Tech OS — Phase 1 demo data ─────────────────────────
import datetime
import random
from decimal import Decimal

from django.utils import timezone

from apps.users.models import User
from apps.org.models import Organization, Department, EmployeeProfile
from apps.leave.models import LeaveType, LeaveRequest
from apps.calendar_app.models import Holiday, CalendarEvent
from apps.calendar_app.utils import working_days
from apps.notices.models import Notice
from apps.attendance.models import AttendanceRecord

DEMO_PASSWORD = "Thimi@12345"
today = timezone.localdate()

org = Organization.load()
org.name = "Thimi Tech"
org.tagline = "Geospatial and AI software, built in Thimi, Bhaktapur, Nepal."
org.about = ("Thimi Tech builds geoportals, municipal management systems, data platforms and "
             "AI assistants for organizations across Nepal.")
org.address = "Thimi, Bhaktapur, Nepal"
org.website = "https://thimitech.com"
org.email = "info@thimitech.com"
org.save()

depts = {name: Department.objects.get_or_create(name=name, defaults={"description": desc})[0]
         for name, desc in [
             ("Engineering", "Web, backend and platform engineering."),
             ("GIS & Mapping", "Spatial data, cartography and geoportal content."),
             ("Operations", "HR, finance and office operations."),
         ]}

# email, first, last, role, department, designation, join, dob, phone, skills
PEOPLE = [
    ("hr@thimitech.com", "Anita", "Karki", "hr_admin", "Operations", "HR & Operations Lead",
     "2022-03-01", "1990-06-12", "9841000101", ["People ops", "Payroll", "Compliance"]),
    ("manager@thimitech.com", "Bikash", "Maharjan", "manager", "Engineering", "Engineering Manager",
     "2021-08-15", "1988-11-03", "9841000102", ["Django", "System design", "Mentoring"]),
    ("sita@thimitech.com", "Sita", "Shrestha", "employee", "Engineering", "Frontend Developer",
     "2023-05-01", "1997-02-20", "9841000103", ["Vue 3", "TypeScript", "Tailwind CSS"]),
    ("hari@thimitech.com", "Hari", "Prajapati", "employee", "Engineering", "Backend Developer",
     "2023-09-10", "1996-08-08", "9841000104", ["Python", "PostgreSQL", "Celery"]),
    ("gis.lead@thimitech.com", "Nabin", "Tamang", "manager", "GIS & Mapping", "GIS Lead",
     "2022-01-10", "1991-04-25", "9841000105", ["QGIS", "PostGIS", "Remote sensing"]),
    ("maya@thimitech.com", "Maya", "Gurung", "employee", "GIS & Mapping", "GIS Analyst",
     "2024-02-01", "1998-12-14", "9841000106", ["QGIS", "Cartography", "Python"]),
    ("applicant@example.com", "Ramesh", "Thapa", "guest", None, "", None, None, "", []),
]

users = {}
for i, (email, first, last, role, dept, title, join, dob, phone, skills) in enumerate(PEOPLE, start=2):
    u, created = User.objects.get_or_create(email=email, defaults={"username": email.split("@")[0]})
    u.first_name, u.last_name, u.role = first, last, role
    if created:
        u.set_password(DEMO_PASSWORD)
    u.save()
    users[email] = u
    if role != "guest":
        EmployeeProfile.objects.update_or_create(user=u, defaults={
            "employee_code": f"TT-{i:03d}", "department": depts[dept], "designation": title,
            "join_date": join, "date_of_birth": dob, "phone": phone, "skills": skills,
            "address": "Bhaktapur, Nepal",
        })

# Super admin: never touch the password; fill the name only if blank.
admin = User.objects.filter(email="admin@thimitech.com").first()
if admin:
    if not admin.first_name:
        admin.first_name, admin.last_name = "Ravi", "Shrestha"
        admin.save()
    EmployeeProfile.objects.update_or_create(user=admin, defaults={
        "employee_code": "TT-001", "department": depts["Operations"], "designation": "Director",
        "join_date": "2020-01-01", "skills": ["Strategy", "Geospatial", "AI"],
        "address": "Thimi, Bhaktapur, Nepal",
    })

depts["Engineering"].manager = users["manager@thimitech.com"]
depts["Engineering"].save()
depts["GIS & Mapping"].manager = users["gis.lead@thimitech.com"]
depts["GIS & Mapping"].save()

LEAVE_TYPES = [
    ("Annual", "annual", 18, True, "#5d7a4f"),
    ("Sick", "sick", 12, True, "#4f6d7a"),
    ("Casual", "casual", 6, True, "#b08d5b"),
    ("Unpaid", "unpaid", 0, False, "#7a6a52"),
    ("Maternity/Paternity", "parental", 0, True, "#d96b34"),  # 0 quota = case-by-case
]
lt = {}
for name, code, quota, paid, color in LEAVE_TYPES:
    lt[code], _ = LeaveType.objects.get_or_create(code=code, defaults={
        "name": name, "annual_quota": quota, "is_paid": paid, "color": color})

SAMPLE = "Sample date — verify against the official Government of Nepal calendar."
HOLIDAYS = [  # (date, name, optional) — lunar dates are approximate
    ("2026-01-11", "Prithvi Jayanti", False), ("2026-01-15", "Maghe Sankranti", False),
    ("2026-01-30", "Martyrs Day", False), ("2026-02-15", "Maha Shivaratri", False),
    ("2026-02-18", "Gyalpo Lhosar", True), ("2026-02-19", "Democracy Day", False),
    ("2026-03-03", "Holi (Fagu Purnima)", False), ("2026-03-08", "International Women's Day", True),
    ("2026-04-14", "Nepali New Year", False), ("2026-05-01", "Labour Day / Buddha Jayanti", False),
    ("2026-05-28", "Republic Day", False), ("2026-08-28", "Janai Purnima", False),
    ("2026-09-04", "Krishna Janmashtami", False), ("2026-09-14", "Haritalika Teej", True),
    ("2026-09-19", "Constitution Day", False), ("2026-10-11", "Ghatasthapana", False),
    ("2026-10-17", "Dashain — Fulpati", False), ("2026-10-18", "Dashain — Maha Ashtami", False),
    ("2026-10-19", "Dashain — Maha Navami", False), ("2026-10-20", "Dashain — Vijaya Dashami", False),
    ("2026-10-21", "Dashain — Ekadashi", False), ("2026-10-22", "Dashain — Dwadashi", False),
    ("2026-11-08", "Tihar — Laxmi Puja", False), ("2026-11-09", "Tihar — Govardhan Puja / Mha Puja", False),
    ("2026-11-10", "Tihar — Bhai Tika", False), ("2026-11-15", "Chhath Parva", False),
    ("2026-12-25", "Christmas Day", False), ("2026-12-30", "Tamu Lhosar", True),
    ("2027-01-11", "Prithvi Jayanti", False), ("2027-01-15", "Maghe Sankranti", False),
    ("2027-01-30", "Martyrs Day", False), ("2027-02-07", "Sonam / Gyalpo Lhosar", True),
    ("2027-02-19", "Democracy Day", False), ("2027-03-06", "Maha Shivaratri", False),
    ("2027-03-22", "Holi (Fagu Purnima)", False), ("2027-04-14", "Nepali New Year", False),
    ("2027-05-01", "Labour Day", False), ("2027-05-20", "Buddha Jayanti", False),
    ("2027-05-29", "Republic Day", False), ("2027-08-17", "Janai Purnima", False),
    ("2027-08-25", "Krishna Janmashtami", False), ("2027-09-04", "Haritalika Teej", True),
    ("2027-09-19", "Constitution Day", False), ("2027-09-30", "Ghatasthapana", False),
    ("2027-10-06", "Dashain — Fulpati", False), ("2027-10-07", "Dashain — Maha Ashtami", False),
    ("2027-10-08", "Dashain — Maha Navami", False), ("2027-10-09", "Dashain — Vijaya Dashami", False),
    ("2027-10-10", "Dashain — Ekadashi", False), ("2027-10-29", "Tihar — Laxmi Puja", False),
    ("2027-10-30", "Tihar — Govardhan Puja / Mha Puja", False), ("2027-10-31", "Tihar — Bhai Tika", False),
    ("2027-11-04", "Chhath Parva", False), ("2027-12-25", "Christmas Day", False),
    ("2027-12-30", "Tamu Lhosar", True),
]
for d, name, optional in HOLIDAYS:
    Holiday.objects.get_or_create(date=d, defaults={"name": name, "is_optional": optional, "description": SAMPLE})


def at(day, hh, mm=0):
    """Aware datetime for a local (Asia/Kathmandu) wall-clock time."""
    return timezone.make_aware(datetime.datetime.combine(day, datetime.time(hh, mm)))


def next_weekday(wd):
    return today + datetime.timedelta(days=(wd - today.weekday()) % 7 or 7)


hr, mgr, gis = users["hr@thimitech.com"], users["manager@thimitech.com"], users["gis.lead@thimitech.com"]
sita, hari, maya = users["sita@thimitech.com"], users["hari@thimitech.com"], users["maya@thimitech.com"]

NOTICES = [
    dict(title="Welcome to Thimi Tech OS", category="hr", pinned=True, author=hr,
         body="Namaste team! Attendance, leave, the calendar and this notice board now live in one place. "
              "Check in when you start your day and apply for leave right here."),
    dict(title="Leave must be applied at least 3 working days in advance", category="urgent", author=hr,
         body="Effective immediately, planned leave (annual/casual) must be requested at least **3 working days** "
              "ahead. Sick leave can be applied on the day; attach a note for absences longer than 2 days."),
    dict(title="Code freeze for the GeoPortal release", category="general", author=mgr,
         audience="department", department=depts["Engineering"],
         body="Engineering: code freeze starts Thursday 17:00. Only release-blocking fixes after that, reviewed by me."),
]
for n in NOTICES:
    Notice.objects.get_or_create(title=n.pop("title"), defaults=n)

# Events are keyed on title, so dates are fixed by the first run.
fri, thu = next_weekday(4), next_weekday(3)
CalendarEvent.objects.get_or_create(title="Monthly all-hands", defaults=dict(
    start=at(fri, 16), end=at(fri, 17), location="Thimi office — main hall", created_by=hr,
    description="Company updates, demos and a welcome for new joiners."))
review, made = CalendarEvent.objects.get_or_create(title="Sprint review — Engineering", defaults=dict(
    start=at(thu, 14), end=at(thu, 15, 30), location="Meeting room 2", audience="department",
    department=depts["Engineering"], created_by=mgr))
if made:
    review.attendees.set([mgr, sita, hari])

past = working_days(today - datetime.timedelta(days=21), today - datetime.timedelta(days=1))[-10:]
upcoming = working_days(today + datetime.timedelta(days=7), today + datetime.timedelta(days=40))


def leave(user, code, start, end, reason, **extra):
    """Keyed on (user, reason) so reruns never duplicate."""
    obj, _ = LeaveRequest.objects.get_or_create(user=user, reason=reason, defaults=dict(
        leave_type=lt[code], start_date=start, end_date=end,
        days=Decimal(len(working_days(start, end))), **extra))
    return obj


hari_sick = leave(hari, "sick", past[-4], past[-4], "Fever — doctor advised rest.",
                  status="approved", approver=mgr, decision_note="Get well soon.",
                  decided_at=at(past[-4], 9, 30))
leave(sita, "annual", upcoming[0], upcoming[2], "Family trip to Pokhara.")           # Bikash approves
leave(mgr, "casual", upcoming[4], upcoming[4], "Personal errand at the land office.")  # HR approves (no manager)

# Attendance for the last 10 working days: stable present/late/remote mix per (user, day).
for u in [hr, mgr, sita, hari, gis, maya]:
    for d in past:
        if u == hari and hari_sick.start_date <= d <= hari_sick.end_date:
            AttendanceRecord.objects.get_or_create(user=u, date=d, defaults={"status": "on_leave"})
            continue
        r = random.Random(f"{u.email}{d}")
        late, remote = r.random() < 0.2, r.random() < 0.15
        ip = "103.10.28.14" if remote else "192.168.1.20"
        AttendanceRecord.objects.get_or_create(user=u, date=d, defaults={
            "check_in": at(d, 10, r.randint(16, 50)) if late else at(d, 9, r.randint(35, 59)),
            "check_out": at(d, 17, r.randint(0, 59)) + datetime.timedelta(minutes=r.randint(0, 60)),
            "status": "late" if late else "present", "work_mode": "remote" if remote else "office",
            "check_in_ip": ip, "check_out_ip": ip,
        })

print("Phase 1:",
      Department.objects.count(), "departments,",
      User.objects.count(), "users,",
      EmployeeProfile.objects.count(), "profiles,",
      LeaveType.objects.count(), "leave types,",
      Holiday.objects.count(), "holidays,",
      Notice.objects.count(), "notices,",
      CalendarEvent.objects.count(), "events,",
      AttendanceRecord.objects.count(), "attendance,",
      LeaveRequest.objects.count(), "leave requests")
