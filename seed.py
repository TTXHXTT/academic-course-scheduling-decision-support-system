#!/usr/bin/env python
"""
ACS Database Seed Script
Seeds administrators, students dataset, and 2025_2026_years_courses dataset from 2025_2026_years_courses.csv.
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


def reset_db():
    print("Dropping all tables...")
    from app.models import user, dataset, course_record, analysis, recommendation, scenario, audit, student_schedule  # noqa
    Base.metadata.drop_all(bind=engine)
    print("Recreating tables...")
    init_db()


def seed_users(session):
    print("Seeding administrators and staff from admin.csv...")
    created = 0

    # 1. Seed administrators and staff from admin.csv
    admin_csv_path = os.path.join(root_dir, "data", "synthetic", "admin.csv")
    if os.path.exists(admin_csv_path):
        with open(admin_csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                email = (row.get("email") or "").strip()
                if not email:
                    continue
                password = row.get("password") or "Admin@CSUSB123"
                full_name = row.get("full_name") or "Administrator"
                role_str = (row.get("role") or "admin").strip()
                student_id = (row.get("student_id") or "").strip() or None

                try:
                    role = UserRole(role_str)
                except ValueError:
                    role = UserRole.admin

                existing = session.query(User).filter(User.email == email).first()
                if not existing:
                    u = User(
                        email=email,
                        student_id=student_id,
                        hashed_password=hash_password(password),
                        full_name=full_name,
                        role=role,
                        is_active=True,
                    )
                    session.add(u)
                    created += 1
                else:
                    existing.hashed_password = hash_password(password)
                    existing.full_name = full_name
                    existing.role = role
                    if student_id:
                        existing.student_id = student_id
                    session.add(existing)

    # 2. Seed students from students.csv
    print("Seeding students from students.csv...")
    students_csv_path = os.path.join(root_dir, "data", "synthetic", "students.csv")
    if os.path.exists(students_csv_path):
        with open(students_csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                s_id = (row.get("studentID") or row.get("student_id") or "").strip() or None
                s_email = (row.get("student_email") or "").strip()
                s_name = row.get("student_name") or (f"Student {s_id}" if s_id else "Student")
                s_pass = row.get("student_password") or "123456"
                role_str = (row.get("role") or "student").strip()

                try:
                    role = UserRole(role_str)
                except ValueError:
                    role = UserRole.student

                if not s_email:
                    continue

                existing = session.query(User).filter(User.email == s_email).first()
                if not existing:
                    stu = User(
                        email=s_email,
                        student_id=s_id,
                        hashed_password=hash_password(s_pass),
                        full_name=s_name,
                        role=role,
                        is_active=True,
                    )
                    session.add(stu)
                    created += 1
                else:
                    existing.hashed_password = hash_password(s_pass)
                    existing.full_name = s_name
                    existing.role = role
                    if s_id:
                        existing.student_id = s_id
                    session.add(existing)

    session.commit()
    print(f"  Created/verified users ({created} new added)")


def seed_courses_dataset(session):
    print("Seeding 2025_2026_years_courses dataset from 2025_2026_years_courses.csv...")
    # Check if dataset named 2025_2026_years_courses already exists
    existing = session.query(Dataset).filter(
        (Dataset.name == "2025_2026_years_courses") | (Dataset.name == "current_courses") | (Dataset.name == "CSUSB Demo Dataset (Synthetic)")
    ).first()
    
    if existing:
        if existing.name != "2025_2026_years_courses":
            existing.name = "2025_2026_years_courses"
            session.commit()
        print("  2025_2026_years_courses dataset already loaded.")
        return existing

    scheduler = session.query(User).filter(User.role == UserRole.academic_scheduler).first()
    
    # Try 2025_2026_years_courses.csv first, then courses.csv, then demo_dataset.csv
    possible_paths = [
        os.path.join(root_dir, "data", "synthetic", "2025_2026_years_courses.csv"),
        os.path.join(root_dir, "data", "synthetic", "courses.csv"),
        os.path.join(root_dir, "data", "synthetic", "current_courses.csv"),
        os.path.join(root_dir, "data", "synthetic", "demo_dataset.csv"),
    ]
    data_path = next((p for p in possible_paths if os.path.exists(p)), None)

    if not data_path:
        print(f"  WARNING: courses dataset not found in data/synthetic/")
        return None

    with open(data_path, "rb") as f:
        content = f.read()

    service = ImportService(session)
    source_fn = os.path.basename(data_path)
    dataset, job = service.import_csv(
        file_content=content,
        dataset_name="2025_2026_years_courses",
        source_filename=source_fn,
        user=scheduler,
        is_synthetic=True,
        description="2025-2026 academic years course offerings and historical schedule dataset.",
    )
    print(f"  Imported 2025_2026_years_courses dataset id={dataset.id}: {job.total_rows} rows, {job.valid_rows} valid")

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
        print("\nSeeded Accounts:")
        users = session.query(User).order_by(User.role, User.email).all()
        for u in users:
            s_id_str = f" [ID: {u.student_id}]" if u.student_id else ""
            print(f"  {u.email} ({u.role.value}){s_id_str}")
    finally:
        session.close()


if __name__ == "__main__":
    main()
