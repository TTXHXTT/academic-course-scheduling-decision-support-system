#!/usr/bin/env python
"""
ACS Database Seed Script
Seeds demonstration users, students dataset, and current_courses from courses.csv.
"""
import sys
import os
import csv
import argparse

root_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, root_dir)

from app.core.database import engine, SessionLocal, init_db, Base
from app.core.security import hash_password
from app.models.user import User, UserRole
from app.models.dataset import Dataset
from app.models.course_record import CourseRecord
from app.models.student_schedule import StudentSchedule
from app.services.import_service import ImportService
from app.services.analysis_service import AnalysisService
from app.services.recommendation_service import RecommendationService


DEMO_USERS = [
    {"email": "000000000@coyote.csusb.edu", "password": "123456", "full_name": "Coyote Administrator", "role": UserRole.admin},
    {"email": "admin@csusb.edu", "password": "Admin@CSUSB123", "full_name": "System Administrator", "role": UserRole.admin},
    {"email": "scheduler@csusb.edu", "password": "Scheduler@123", "full_name": "Alex Scheduler", "role": UserRole.academic_scheduler},
    {"email": "chair@csusb.edu", "password": "Chair@123", "full_name": "Dr. Department Chair", "role": UserRole.department_chair},
    {"email": "coordinator@csusb.edu", "password": "Coord@123", "full_name": "Pat Coordinator", "role": UserRole.program_coordinator},
    {"email": "007455611@coyote.csusb.edu", "password": "123456", "full_name": "Bao Ngo", "student_id": "007455611", "role": UserRole.student},
    {"email": "006890631@coyote.csusb.edu", "password": "123456", "full_name": "Brandon Varela Padilla", "student_id": "006890631", "role": UserRole.student},
    {"email": "009146235@coyote.csusb.edu", "password": "123456", "full_name": "Xiangyu Qu", "student_id": "009146235", "role": UserRole.student},
    {"email": "007543322@coyote.csusb.edu", "password": "123456", "full_name": "Savannah Hebert", "student_id": "007543322", "role": UserRole.student},
    {"email": "008770314@coyote.csusb.edu", "password": "123456", "full_name": "Shraddha Paithankar", "student_id": "008770314", "role": UserRole.student},
    {"email": "008123456@coyote.csusb.edu", "password": "123456", "full_name": "Erik Marvin", "student_id": "008123456", "role": UserRole.student},
]


def reset_db():
    print("Dropping all tables...")
    from app.models import user, dataset, course_record, analysis, recommendation, scenario, audit, student_schedule  # noqa
    Base.metadata.drop_all(bind=engine)
    print("Recreating tables...")
    init_db()


def seed_users(session):
    print("Seeding demonstration users and students...")
    created = 0
    for u in DEMO_USERS:
        existing = session.query(User).filter(User.email == u["email"]).first()
        if not existing:
            user = User(
                email=u["email"],
                student_id=u.get("student_id"),
                hashed_password=hash_password(u["password"]),
                full_name=u["full_name"],
                role=u["role"],
                is_active=True,
            )
            session.add(user)
            created += 1
        else:
            if u.get("student_id") and not existing.student_id:
                existing.student_id = u["student_id"]
            existing.hashed_password = hash_password(u["password"])
            existing.full_name = u["full_name"]
            existing.role = u["role"]
            session.add(existing)

    # Also seed students from students.csv
    students_csv_path = os.path.join(root_dir, "data", "synthetic", "students.csv")
    if os.path.exists(students_csv_path):
        with open(students_csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                s_id = row.get("studentID") or row.get("student_id")
                s_email = row.get("student_email")
                s_name = row.get("student_name") or f"Student {s_id}"
                s_pass = row.get("student_password") or "123456"
                if s_email and not session.query(User).filter(User.email == s_email).first():
                    stu = User(
                        email=s_email,
                        student_id=s_id,
                        hashed_password=hash_password(s_pass),
                        full_name=s_name,
                        role=UserRole.student,
                        is_active=True,
                    )
                    session.add(stu)
                    created += 1

    session.commit()
    print(f"  Created/verified users ({created} new added)")


def seed_courses_dataset(session):
    print("Seeding current_courses dataset from courses.csv...")
    # Check if dataset named current_courses already exists
    existing = session.query(Dataset).filter(
        (Dataset.name == "current_courses") | (Dataset.name == "CSUSB Demo Dataset (Synthetic)")
    ).first()
    
    if existing:
        if existing.name != "current_courses":
            existing.name = "current_courses"
            session.commit()
        print("  current_courses dataset already loaded.")
        return existing

    scheduler = session.query(User).filter(User.role == UserRole.academic_scheduler).first()
    
    # Try current_courses.csv first, then courses.csv, then demo_dataset.csv
    possible_paths = [
        os.path.join(root_dir, "data", "synthetic", "current_courses.csv"),
        os.path.join(root_dir, "data", "synthetic", "courses.csv"),
        os.path.join(root_dir, "data", "synthetic", "demo_dataset.csv"),
    ]
    data_path = next((p for p in possible_paths if os.path.exists(p)), None)

    if not data_path:
        print(f"  WARNING: courses dataset not found in data/synthetic/")
        return None

    with open(data_path, "rb") as f:
        content = f.read()

    service = ImportService(session)
    dataset, job = service.import_csv(
        file_content=content,
        dataset_name="current_courses",
        source_filename="courses.csv",
        user=scheduler,
        is_synthetic=True,
        description="Current course offerings and historical schedule dataset.",
    )
    print(f"  Imported current_courses dataset id={dataset.id}: {job.total_rows} rows, {job.valid_rows} valid")

    if job.valid_rows > 0:
        print("  Running baseline demand analysis...")
        analysis_service = AnalysisService(session)
        run = analysis_service.run_analysis(
            dataset_id=dataset.id,
            user=scheduler,
            name="Baseline Analysis",
            is_baseline=True,
        )
        print(f"  Analysis run id={run.id}: {run.courses_analyzed} courses analyzed")
        rec_service = RecommendationService(session)
        recs = rec_service.generate_recommendations(run.id)
        print(f"  Generated {len(recs)} recommendations")
        
    return dataset


def seed_demo_student_schedule(session):
    """Pre-enroll the student user in initial classes so they can see class information immediately."""
    student_user = session.query(User).filter(User.email == "007455611@coyote.csusb.edu").first()
    if not student_user:
        return

    # Check if student already has schedule
    existing_count = session.query(StudentSchedule).filter(StudentSchedule.user_id == student_user.id).count()
    if existing_count > 0:
        print(f"  Student {student_user.email} already has {existing_count} classes in schedule.")
        return

    # Pick 2-3 sample classes from courses in the database
    sample_courses = session.query(CourseRecord).limit(3).all()
    for c in sample_courses:
        sched = StudentSchedule(
            user_id=student_user.id,
            student_id="007455611",
            course_record_id=c.id,
            status="Enrolled",
        )
        session.add(sched)
    session.commit()
    print(f"  Pre-enrolled student {student_user.email} in {len(sample_courses)} classes.")


def main():
    parser = argparse.ArgumentParser(description="Seed the ACS database")
    parser.add_argument("--reset", action="store_true", help="Drop and recreate all tables")
    args = parser.parse_args()
    if args.reset:
        reset_db()
    else:
        print("Initializing database tables...")
        init_db()
    session = SessionLocal()
    try:
        seed_users(session)
        seed_courses_dataset(session)
        seed_demo_student_schedule(session)
        print("\nSeed complete!")
        print("\nAccounts:")
        for u in DEMO_USERS:
            print(f"  {u['email']} / {u['password']} ({u['role'].value})")
    finally:
        session.close()


if __name__ == "__main__":
    main()
