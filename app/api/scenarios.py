"""
What-if scenario API endpoints.
Implements FR-07, FR-08, Module G.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.scenario import Scenario
from app.models.user import User
from app.schemas.scenario import ScenarioCreate, ScenarioResponse
from app.services.scenario_service import ScenarioService
from app.services.audit_service import AuditService
from app.api.deps import get_current_user

router = APIRouter(prefix="/api/scenarios", tags=["scenarios"])


@router.post("/", response_model=ScenarioResponse)
def create_scenario(
    data: ScenarioCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create and execute a what-if scenario."""
    service = ScenarioService(db)
    scenario = service.create_and_run_scenario(
        name=data.name,
        description=data.description,
        baseline_analysis_id=data.baseline_analysis_id,
        scenario_type=data.scenario_type,
        parameters=data.parameters,
        user=current_user,
    )
    AuditService(db).log(
        "scenario.created",
        actor=current_user,
        entity_type="Scenario",
        entity_id=scenario.id,
        detail=f"Created scenario '{scenario.name}' type={scenario.scenario_type}"
    )
    scenario.results  # trigger lazy load
    return scenario


@router.get("/", response_model=List[ScenarioResponse])
def list_scenarios(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    scenarios = db.query(Scenario).order_by(Scenario.created_at.desc()).all()
    for s in scenarios:
        s.results  # trigger lazy load
    return scenarios


@router.get("/{scenario_id}", response_model=ScenarioResponse)
def get_scenario(
    scenario_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    scenario = db.get(Scenario, scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    scenario.results  # trigger lazy load
    return scenario
