"""
Dataset management API endpoints.
Implements FR-01, DR-01, DR-02, Module B, Module C.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import settings
from app.models.dataset import Dataset, ImportJob, ValidationIssue
from app.models.user import User
from app.schemas.dataset import DatasetResponse, ImportJobResponse, ValidationIssueResponse
from app.services.import_service import ImportService
from app.services.audit_service import AuditService
from app.api.deps import get_current_user, can_import_data

router = APIRouter(prefix="/api/datasets", tags=["datasets"])


@router.get("/", response_model=List[DatasetResponse])
def list_datasets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all imported datasets."""
    return db.query(Dataset).order_by(Dataset.imported_at.desc()).all()


@router.get("/{dataset_id}", response_model=DatasetResponse)
def get_dataset(
    dataset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    dataset = db.get(Dataset, dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return dataset


@router.post("/upload")
async def upload_dataset(
    file: UploadFile = File(...),
    name: str = Form(...),
    description: Optional[str] = Form(default=None),
    is_synthetic: bool = Form(default=False),
    db: Session = Depends(get_db),
    current_user: User = Depends(can_import_data),
):
    """Upload and import a CSV dataset. Only academic schedulers and admins."""
    # Validate file type
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported.")

    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size: {settings.MAX_UPLOAD_SIZE_BYTES // 1024 // 1024} MB"
        )
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    service = ImportService(db)
    dataset, job = service.import_csv(
        file_content=content,
        dataset_name=name,
        source_filename=file.filename,
        user=current_user,
        is_synthetic=is_synthetic,
        description=description,
    )

    AuditService(db).log(
        "dataset.import",
        actor=current_user,
        entity_type="Dataset",
        entity_id=dataset.id,
        detail=f"Imported '{dataset.name}': {job.total_rows} rows, {job.valid_rows} valid, {job.error_rows} errors"
    )

    return {
        "dataset_id": dataset.id,
        "status": dataset.status.value,
        "total_rows": job.total_rows,
        "valid_rows": job.valid_rows,
        "error_rows": job.error_rows,
        "warning_rows": job.warning_rows,
        "import_job_id": job.id,
    }


@router.get("/{dataset_id}/import-jobs", response_model=List[ImportJobResponse])
def get_import_jobs(
    dataset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    jobs = db.query(ImportJob).filter(ImportJob.dataset_id == dataset_id).all()
    # Eagerly load validation issues for each job
    for job in jobs:
        job.validation_issues  # trigger lazy load
    return jobs


@router.get("/{dataset_id}/validation-issues", response_model=List[ValidationIssueResponse])
def get_validation_issues(
    dataset_id: int,
    severity: Optional[str] = Query(None),
    limit: int = Query(default=200, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get validation issues for a dataset."""
    jobs = db.query(ImportJob).filter(ImportJob.dataset_id == dataset_id).all()
    job_ids = [j.id for j in jobs]
    if not job_ids:
        return []

    q = db.query(ValidationIssue).filter(ValidationIssue.import_job_id.in_(job_ids))
    if severity:
        q = q.filter(ValidationIssue.severity == severity)
    return q.limit(limit).all()


@router.delete("/{dataset_id}")
def delete_dataset(
    dataset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(can_import_data),
):
    """Delete a dataset and all its records. Requires scheduler or admin role."""
    dataset = db.get(Dataset, dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    AuditService(db).log(
        "dataset.deleted",
        actor=current_user,
        entity_type="Dataset",
        entity_id=dataset_id,
        detail=f"Deleted dataset '{dataset.name}'"
    )
    db.delete(dataset)
    db.commit()
    return {"message": "Dataset deleted"}
