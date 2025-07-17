# Production use requires a separate commercial license from the Licensor.
# For commercial licenses, please contact Tiago Sasaki at tiago@confenge.com.br.

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from ...db.database import get_db
from ...auth.dependencies import get_current_active_user
from ...db.models.project import User
from ...services.analytics_service import get_portfolio_overview, get_conflicts_by_discipline, get_cost_analysis, get_project_performance_metrics

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/portfolio/overview")
def portfolio_overview(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get comprehensive portfolio overview with KPIs across all user's projects:
    - Total conflicts by discipline
    - Average resolution cost and time
    - Project performance metrics
    """
    try:
        stats = get_portfolio_overview(db, current_user.id)
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating portfolio overview: {str(e)}")


@router.get("/conflicts/by-discipline")
def conflicts_by_discipline(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get conflict distribution by discipline pairs for dashboard visualization
    """
    try:
        stats = get_conflicts_by_discipline(db, current_user.id)
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting conflicts by discipline: {str(e)}")


@router.get("/costs/analysis")
def cost_analysis(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get cost analysis across projects including:
    - Average resolution costs by conflict type
    - Total project costs breakdown
    - Cost trends over time
    """
    try:
        stats = get_cost_analysis(db, current_user.id)
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating cost analysis: {str(e)}")


@router.get("/performance/metrics")
def performance_metrics(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get performance metrics including:
    - Average resolution time by conflict type
    - Success rates of different solution types
    - Project completion statistics
    """
    try:
        stats = get_project_performance_metrics(db, current_user.id)
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating performance metrics: {str(e)}")


@router.get("/projects/{project_id}/analytics")
def project_specific_analytics(
    project_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get analytics for a specific project
    """
    from ...db.models.project import Project
    
    # Verify project ownership
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    try:
        from ...services.analytics_service import get_project_analytics
        stats = get_project_analytics(db, project_id)
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating project analytics: {str(e)}")