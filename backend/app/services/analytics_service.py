# Production use requires a separate commercial license from the Licensor.
# For commercial licenses, please contact Tiago Sasaki at tiago@confenge.com.br.

from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from ..db.models.project import Project, Conflict, Solution, SolutionFeedback, ProjectCost
from ..db.models.analytics import HistoricalConflict


def get_portfolio_overview(db: Session, user_id: int) -> Dict[str, Any]:
    """
    Get comprehensive portfolio overview with KPIs across all user's projects
    """
    # Get user's projects
    user_projects = db.query(Project.id).filter(Project.owner_id == user_id).subquery()
    
    # Total projects count
    total_projects = db.query(Project).filter(Project.owner_id == user_id).count()
    
    # Total conflicts count
    total_conflicts = db.query(Conflict).filter(
        Conflict.project_id.in_(user_projects)
    ).count()
    
    # Conflicts by status
    conflicts_by_status = db.query(
        Conflict.status,
        func.count(Conflict.id).label('count')
    ).filter(
        Conflict.project_id.in_(user_projects)
    ).group_by(Conflict.status).all()
    
    # Conflicts by severity
    conflicts_by_severity = db.query(
        Conflict.severity,
        func.count(Conflict.id).label('count')
    ).filter(
        Conflict.project_id.in_(user_projects)
    ).group_by(Conflict.severity).all()
    
    # Active projects (with recent activity)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    active_projects = db.query(Project).filter(
        Project.owner_id == user_id,
        Project.updated_at >= thirty_days_ago
    ).count()
    
    # Average solution confidence
    avg_confidence = db.query(
        func.avg(Solution.confidence_score)
    ).join(Conflict).filter(
        Conflict.project_id.in_(user_projects)
    ).scalar() or 0.0
    
    return {
        "total_projects": total_projects,
        "active_projects": active_projects,
        "total_conflicts": total_conflicts,
        "average_solution_confidence": round(float(avg_confidence), 2),
        "conflicts_by_status": [
            {"status": status, "count": count} for status, count in conflicts_by_status
        ],
        "conflicts_by_severity": [
            {"severity": severity, "count": count} for severity, count in conflicts_by_severity
        ]
    }


def get_conflicts_by_discipline(db: Session, user_id: int) -> Dict[str, Any]:
    """
    Get conflict distribution by discipline pairs using HistoricalConflict data
    """
    # Get user's projects
    user_projects = db.query(Project.id).filter(Project.owner_id == user_id).subquery()
    
    # Get conflicts by discipline from historical data
    discipline_conflicts = db.query(
        HistoricalConflict.discipline_1,
        HistoricalConflict.discipline_2,
        func.count(HistoricalConflict.id).label('conflict_count'),
        func.avg(HistoricalConflict.resolution_cost).label('avg_cost'),
        func.avg(HistoricalConflict.resolution_time_days).label('avg_time')
    ).filter(
        HistoricalConflict.project_id.in_(user_projects)
    ).group_by(
        HistoricalConflict.discipline_1,
        HistoricalConflict.discipline_2
    ).order_by(desc('conflict_count')).all()
    
    # Also get current conflicts by type (since we don't have discipline data in Conflict model)
    current_conflicts = db.query(
        Conflict.conflict_type,
        func.count(Conflict.id).label('count')
    ).filter(
        Conflict.project_id.in_(user_projects)
    ).group_by(Conflict.conflict_type).order_by(desc('count')).all()
    
    return {
        "discipline_conflicts": [
            {
                "discipline_1": disc1,
                "discipline_2": disc2,
                "conflict_count": int(count),
                "avg_resolution_cost": float(avg_cost) if avg_cost else 0.0,
                "avg_resolution_time_days": float(avg_time) if avg_time else 0.0
            }
            for disc1, disc2, count, avg_cost, avg_time in discipline_conflicts
        ],
        "conflicts_by_type": [
            {"conflict_type": conflict_type, "count": count}
            for conflict_type, count in current_conflicts
        ]
    }


def get_cost_analysis(db: Session, user_id: int) -> Dict[str, Any]:
    """
    Get comprehensive cost analysis across projects
    """
    # Get user's projects
    user_projects = db.query(Project.id).filter(Project.owner_id == user_id).subquery()
    
    # Total project costs by parameter
    cost_breakdown = db.query(
        ProjectCost.parameter_name,
        func.sum(ProjectCost.cost).label('total_cost'),
        func.avg(ProjectCost.cost).label('avg_cost'),
        func.count(ProjectCost.id).label('projects_count')
    ).filter(
        ProjectCost.project_id.in_(user_projects)
    ).group_by(ProjectCost.parameter_name).all()
    
    # Historical resolution costs by conflict type
    resolution_costs = db.query(
        HistoricalConflict.conflict_type,
        func.avg(HistoricalConflict.resolution_cost).label('avg_cost'),
        func.min(HistoricalConflict.resolution_cost).label('min_cost'),
        func.max(HistoricalConflict.resolution_cost).label('max_cost'),
        func.count(HistoricalConflict.id).label('sample_size')
    ).filter(
        HistoricalConflict.project_id.in_(user_projects),
        HistoricalConflict.resolution_cost.isnot(None)
    ).group_by(HistoricalConflict.conflict_type).all()
    
    # Solution costs from current conflicts
    solution_costs = db.query(
        Solution.solution_type,
        func.avg(Solution.estimated_cost).label('avg_estimated_cost'),
        func.count(Solution.id).label('solution_count')
    ).join(Conflict).filter(
        Conflict.project_id.in_(user_projects),
        Solution.estimated_cost.isnot(None)
    ).group_by(Solution.solution_type).all()
    
    return {
        "project_cost_breakdown": [
            {
                "parameter_name": param,
                "total_cost": float(total),
                "average_cost": float(avg),
                "projects_count": int(count)
            }
            for param, total, avg, count in cost_breakdown
        ],
        "historical_resolution_costs": [
            {
                "conflict_type": conflict_type,
                "avg_cost": float(avg_cost) if avg_cost else 0.0,
                "min_cost": float(min_cost) if min_cost else 0.0,
                "max_cost": float(max_cost) if max_cost else 0.0,
                "sample_size": int(sample_size)
            }
            for conflict_type, avg_cost, min_cost, max_cost, sample_size in resolution_costs
        ],
        "solution_estimated_costs": [
            {
                "solution_type": solution_type,
                "avg_estimated_cost": float(avg_cost / 100.0) if avg_cost else 0.0,  # Convert from cents
                "solution_count": int(count)
            }
            for solution_type, avg_cost, count in solution_costs
        ]
    }


def get_project_performance_metrics(db: Session, user_id: int) -> Dict[str, Any]:
    """
    Get performance metrics including resolution times and success rates
    """
    # Get user's projects
    user_projects = db.query(Project.id).filter(Project.owner_id == user_id).subquery()
    
    # Resolution time analysis from historical data
    resolution_times = db.query(
        HistoricalConflict.conflict_type,
        func.avg(HistoricalConflict.resolution_time_days).label('avg_time'),
        func.min(HistoricalConflict.resolution_time_days).label('min_time'),
        func.max(HistoricalConflict.resolution_time_days).label('max_time')
    ).filter(
        HistoricalConflict.project_id.in_(user_projects),
        HistoricalConflict.resolution_time_days.isnot(None)
    ).group_by(HistoricalConflict.conflict_type).all()
    
    # Solution success rates based on feedback
    solution_success_rates = db.query(
        Solution.solution_type,
        func.avg(
            func.case(
                (SolutionFeedback.effectiveness_rating >= 4, 1.0),
                else_=0.0
            )
        ).label('success_rate'),
        func.count(SolutionFeedback.id).label('feedback_count')
    ).join(SolutionFeedback).join(Conflict).filter(
        Conflict.project_id.in_(user_projects),
        SolutionFeedback.effectiveness_rating.isnot(None)
    ).group_by(Solution.solution_type).all()
    
    # Overall feedback ratings
    feedback_distribution = db.query(
        SolutionFeedback.effectiveness_rating,
        func.count(SolutionFeedback.id).label('count')
    ).join(Conflict).filter(
        Conflict.project_id.in_(user_projects),
        SolutionFeedback.effectiveness_rating.isnot(None)
    ).group_by(SolutionFeedback.effectiveness_rating).all()
    
    # Project completion stats
    project_status_stats = db.query(
        Project.status,
        func.count(Project.id).label('count')
    ).filter(Project.owner_id == user_id).group_by(Project.status).all()
    
    return {
        "resolution_time_metrics": [
            {
                "conflict_type": conflict_type,
                "avg_resolution_days": float(avg_time) if avg_time else 0.0,
                "min_resolution_days": float(min_time) if min_time else 0.0,
                "max_resolution_days": float(max_time) if max_time else 0.0
            }
            for conflict_type, avg_time, min_time, max_time in resolution_times
        ],
        "solution_success_rates": [
            {
                "solution_type": solution_type,
                "success_rate": float(success_rate) if success_rate else 0.0,
                "feedback_count": int(feedback_count)
            }
            for solution_type, success_rate, feedback_count in solution_success_rates
        ],
        "feedback_distribution": [
            {"rating": int(rating), "count": int(count)}
            for rating, count in feedback_distribution
        ],
        "project_status_distribution": [
            {"status": status, "count": int(count)}
            for status, count in project_status_stats
        ]
    }


def get_project_analytics(db: Session, project_id: int) -> Dict[str, Any]:
    """
    Get analytics for a specific project
    """
    # Basic project info
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        return {"error": "Project not found"}
    
    # Conflicts in this project
    total_conflicts = db.query(Conflict).filter(Conflict.project_id == project_id).count()
    
    conflicts_by_type = db.query(
        Conflict.conflict_type,
        func.count(Conflict.id).label('count')
    ).filter(Conflict.project_id == project_id).group_by(Conflict.conflict_type).all()
    
    conflicts_by_severity = db.query(
        Conflict.severity,
        func.count(Conflict.id).label('count')
    ).filter(Conflict.project_id == project_id).group_by(Conflict.severity).all()
    
    # Solutions for this project
    solutions_count = db.query(Solution).join(Conflict).filter(
        Conflict.project_id == project_id
    ).count()
    
    avg_confidence = db.query(
        func.avg(Solution.confidence_score)
    ).join(Conflict).filter(
        Conflict.project_id == project_id
    ).scalar() or 0.0
    
    # Project costs
    project_costs = db.query(ProjectCost).filter(
        ProjectCost.project_id == project_id
    ).all()
    
    total_project_cost = sum(cost.cost for cost in project_costs)
    
    return {
        "project_id": project_id,
        "project_name": project.name,
        "project_status": project.status,
        "total_conflicts": total_conflicts,
        "total_solutions": solutions_count,
        "avg_solution_confidence": round(float(avg_confidence), 2),
        "total_project_cost": total_project_cost,
        "conflicts_by_type": [
            {"conflict_type": conflict_type, "count": count}
            for conflict_type, count in conflicts_by_type
        ],
        "conflicts_by_severity": [
            {"severity": severity, "count": count}
            for severity, count in conflicts_by_severity
        ],
        "cost_breakdown": [
            {
                "parameter_name": cost.parameter_name,
                "cost": cost.cost,
                "updated_at": cost.updated_at
            }
            for cost in project_costs
        ]
    }