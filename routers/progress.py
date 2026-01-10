"""
Progress Router
User statistics and analytics
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from database import get_db
from models import User, UserProgress, QuestionSession
from schemas import ProgressResponse, ProgressSummary
from core.dependencies import get_current_user, admin_required
from datetime import datetime, timezone, timedelta
from typing import Optional

router = APIRouter(prefix="/progress", tags=["Progress"])

# ============================================================================
# GET CURRENT USER PROGRESS
# ============================================================================

@router.get("/me", response_model=ProgressResponse)
def get_my_progress(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current user's progress statistics
    
    Returns:
    - Total sessions completed
    - Total questions answered
    - Overall accuracy
    - Subject-wise breakdown
    - Recent activity
    """
    
    progress = db.query(UserProgress).filter(
        UserProgress.user_id == current_user.user_id
    ).first()
    
    if not progress:
        # Create empty progress if doesn't exist
        progress = UserProgress(
            user_id=current_user.user_id,
            total_sessions=0,
            total_questions=0,
            total_correct=0,
            overall_accuracy=0.0,
            subject_stats={},
            last_activity=datetime.now(timezone.utc)
        )
        db.add(progress)
        db.commit()
        db.refresh(progress)
    
    return {
        "user_id": progress.user_id,
        "total_sessions": progress.total_sessions or 0,
        "total_questions": progress.total_questions or 0,
        "total_correct": progress.total_correct or 0,
        "overall_accuracy": progress.overall_accuracy or 0.0,
        "subject_stats": progress.subject_stats or {},
        "last_activity": progress.last_activity,
        "updated_at": progress.updated_at
    }

# ============================================================================
# GET PROGRESS SUMMARY
# ============================================================================

@router.get("/summary", response_model=ProgressSummary)
def get_progress_summary(
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get progress summary for specified period
    
    Query Parameters:
    - days: Number of days to analyze (default: 30)
    
    Returns:
    - Sessions count in period
    - Questions answered in period
    - Accuracy trend
    - Most practiced subjects
    """
    
    # Calculate date range
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)
    
    # Get sessions in period
    sessions = db.query(QuestionSession).filter(
        QuestionSession.user_id == current_user.user_id,
        QuestionSession.created_at >= start_date,
        QuestionSession.created_at <= end_date
    ).all()
    
    # Calculate statistics
    total_sessions = len(sessions)
    
    # FIXED: Added check for both 'selesai' and 'completed' to match database status
    completed_sessions = len([s for s in sessions if s.status in ['selesai', 'completed']])
    total_questions = sum(s.total_questions for s in sessions if s.total_questions)
    
    # Calculate average score
    # FIXED: Included 'completed' status in filter
    completed_with_score = [
        s for s in sessions 
        if s.status in ['selesai', 'completed'] and s.score is not None and s.max_score and s.max_score > 0
    ]
    
    avg_score = 0.0
    if completed_with_score:
        total_percentage = sum((s.score / s.max_score * 100) for s in completed_with_score)
        avg_score = total_percentage / len(completed_with_score)
    
    # Subject breakdown
    subject_breakdown = {}
    for session in sessions:
        # FIXED: Included 'completed' status in filter
        if session.status in ['selesai', 'completed'] and session.results:
            by_subject = session.results.get('by_subject', {})
            for subject, stats in by_subject.items():
                if subject not in subject_breakdown:
                    subject_breakdown[subject] = {
                        'total': 0,
                        'correct': 0,
                        'accuracy': 0.0
                    }
                subject_breakdown[subject]['total'] += stats.get('total', 0)
                subject_breakdown[subject]['correct'] += stats.get('correct', 0)
    
    # Calculate subject accuracies
    for subject in subject_breakdown:
        total = subject_breakdown[subject]['total']
        correct = subject_breakdown[subject]['correct']
        subject_breakdown[subject]['accuracy'] = round((correct / total * 100), 2) if total > 0 else 0.0
    
    return {
        "period_days": days,
        "start_date": start_date,
        "end_date": end_date,
        "total_sessions": total_sessions,
        "completed_sessions": completed_sessions,
        "total_questions": total_questions,
        "average_score": round(avg_score, 2),
        "subject_breakdown": subject_breakdown
    }

# ============================================================================
# GET SUBJECT-SPECIFIC PROGRESS
# ============================================================================

@router.get("/by-subject/{subject}")
def get_subject_progress(
    subject: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get detailed progress for specific subject
    
    Path Parameters:
    - subject: Subject name (tiu, wawasan_kebangsaan, etc.)
    """
    
    progress = db.query(UserProgress).filter(
        UserProgress.user_id == current_user.user_id
    ).first()
    
    if not progress or not progress.subject_stats:
        return {
            "subject": subject,
            "total": 0,
            "correct": 0,
            "accuracy": 0.0,
            "message": "No data available for this subject"
        }
    
    subject_data = progress.subject_stats.get(subject, {
        "total": 0,
        "correct": 0,
        "accuracy": 0.0
    })
    
    return {
        "subject": subject,
        "total": subject_data.get('total', 0),
        "correct": subject_data.get('correct', 0),
        "accuracy": subject_data.get('accuracy', 0.0)
    }

# ============================================================================
# GET ALL USERS PROGRESS (Admin only)
# ============================================================================

@router.get("/all")
def get_all_progress(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(admin_required),
    db: Session = Depends(get_db)
):
    """
    Get progress statistics for all users (Admin only)
    
    Query Parameters:
    - skip: Pagination offset
    - limit: Number of results
    """
    
    query = db.query(UserProgress).order_by(UserProgress.total_sessions.desc())
    
    total = query.count()
    progress_records = query.offset(skip).limit(limit).all()
    
    results = []
    for p in progress_records:
        user = db.query(User).filter(User.user_id == p.user_id).first()
        results.append({
            "user_id": p.user_id,
            "username": user.username if user else "Unknown",
            "full_name": user.full_name if user else "Unknown",
            "total_sessions": p.total_sessions or 0,
            "total_questions": p.total_questions or 0,
            "total_correct": p.total_correct or 0,
            "overall_accuracy": p.overall_accuracy or 0.0,
            "last_activity": p.last_activity
        })
    
    return {
        "progress": results,
        "total": total,
        "skip": skip,
        "limit": limit
    }