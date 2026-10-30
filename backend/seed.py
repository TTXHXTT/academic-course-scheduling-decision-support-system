#!/usr/bin/env python
"""
ACS Database Seed Script

Demonstration accounts (development only):
  admin@csusb.edu          / Admin@CSUSB123  (admin)
  scheduler@csusb.edu      / Scheduler@123   (academic_scheduler)
  chair@csusb.edu          / Chair@123       (department_chair)
  coordinator@csusb.edu    / Coord@123       (program_coordinator)

Usage:
  cd backend
  python seed.py
  python seed.py --reset
"""
import sys
import os
import argparse

backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)

from app.core.database import engine, SessionLocal, init_db, Base
from app.core.security import hash_password
from app.models.user import User, UserRole
from app.models.dataset import Dataset
from app.services.import_service import ImportService
from app.services.analysis_service import AnalysisService
from app.services.recommendation_service import RecommendationService


DEMO_USERS = [
    {"email": "000000000@coyote.csusb.edu", "password": "123456", "full_name": "Coyote Administrator", "role": UserRole.admin},
    {"email": "admin@csusb.edu", "password": "Admin@CSUSB123", "full_name": "System Administrator", "role": UserRole.admin},
    {"email": "scheduler@csusb.edu", "password": "Scheduler@123", "full_name": "Alex Scheduler", "role": UserRole.academic_scheduler},
    {"email": "chair@csusb.edu", "password": "Chair@123", "full_name": "Dr. Department Chair", "role": UserRole.department_chair},
    {"email": "coordinator@csusb.edu", "password": "Coord@123", "full_name": "Pat Coordinator", "role": UserRole.program_coordinator},
    {"email": "007455611@coyote.csusb.edu", "password": "123456", "full_name": "Student Coyote", "role": UserRole.student},
]


def reset_db():
    print("Dropping all tables...")
    from app.models import user, dataset, course_record, analysis, recommendation, scenario, audit  # noqa
    Base.metadata.drop_all(bind=engine)
    print("Recreating tables...")
    init_db()


def seed_users(session):
    print("Seeding demonstration users...")
    created = 0
    for u in DEMO_USERS:
        if not session.query(User).filter(User.email == u["email"]).first():
            user = User(
                email=u["email"],
                hashed_password=hash_password(u["password"]),
                full_name=u["full_name"],
                role=u["role"],
                is_active=True,
            )
            session.add(user)
            created += 1
    session.commit()
    print(f"  Created {created} new users ({len(DEMO_USERS) - created} already existed)")


def seed_demo_dataset(session):
    print("Seeding synthetic demo dataset...")
    if session.query(Dataset).filter(Dataset.name == "CSUSB Demo Dataset (Synthetic)").first():
        print("  Demo dataset already exists, skipping.")
        return None

    scheduler = session.query(User).filter(User.role == UserRole.academic_scheduler).first()
    data_path = os.path.join(os.path.dirname(backend_dir), "data", "synthetic", "demo_dataset.csv")

    if not os.path.exists(data_path):
        print(f"  WARNING: Demo dataset not found at {data_path}")
        return None

    with open(data_path, "rb") as f:
        content = f.read()

    service = ImportService(session)
    dataset, job = service.import_csv(
        file_content=content,
        dataset_name="CSUSB Demo Dataset (Synthetic)",
        source_filename="demo_dataset.csv",
        user=scheduler,
        is_synthetic=True,
        description="[SYNTHETIC DATA - NOT ACTUAL CSUSB DATA] Demonstration dataset for ACS system. Generated for CSE 6550 project.",
    )
    print(f"  Imported dataset id={dataset.id}: {job.total_rows} rows, {job.valid_rows} valid, {job.error_rows} errors")

    if job.valid_rows > 0:
        print("  Running demand analysis...")
        analysis_service = AnalysisService(session)
        run = analysis_service.run_analysis(
            dataset_id=dataset.id,
            user=scheduler,
            name="Initial Demo Analysis",
            is_baseline=True,
        )
        print(f"  Analysis run id={run.id}: {run.courses_analyzed} courses analyzed")
        print("  Generating recommendations...")
        rec_service = RecommendationService(session)
        recs = rec_service.generate_recommendations(run.id)
        print(f"  Generated {len(recs)} recommendations")
    return dataset


def seed_validation_dataset(session):
    print("Seeding validation fixtures dataset...")
    if session.query(Dataset).filter(Dataset.name == "Validation Fixtures (Synthetic - Problematic Records)").first():
        print("  Validation dataset already exists, skipping.")
        return

    scheduler = session.query(User).filter(User.role == UserRole.academic_scheduler).first()
    data_path = os.path.join(os.path.dirname(backend_dir), "data", "synthetic", "validation_fixtures.csv")

    if not os.path.exists(data_path):
        print(f"  WARNING: Validation fixtures not found at {data_path}")
        return

    with open(data_path, "rb") as f:
        content = f.read()

    service = ImportService(session)
    dataset, job = service.import_csv(
        file_content=content,
        dataset_name="Validation Fixtures (Synthetic - Problematic Records)",
        source_filename="validation_fixtures.csv",
        user=scheduler,
        is_synthetic=True,
        description="[SYNTHETIC DATA] Intentionally problematic records for demonstrating the data validation system.",
    )
    print(f"  Imported validation dataset id={dataset.id}: {job.total_rows} rows, {job.valid_rows} valid, {job.error_rows} errors, {job.warning_rows} warnings")


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
        seed_demo_dataset(session)
        seed_validation_dataset(session)
        print("\nSeed complete!")
        print("\nDemo accounts:")
        for u in DEMO_USERS:
            print(f"  {u['email']} / {u['password']} ({u['role'].value})")
    finally:
        session.close()


if __name__ == "__main__":
    main()
