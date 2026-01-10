"""
Admin Router - Complete
Dashboard Statistics + User Management + Audit Logs

ADMIN ONLY - All endpoints require admin role
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_
from database import get_db
from models import User, Question, QuestionSession, UserProgress, AuditLog
from schemas import DashboardStats, AuditLogList
from core.dependencies import admin_required
from core.security import get_password_hash
from datetime import datetime, timezone, timedelta
from typing import Optional
from pydantic import BaseModel

router = APIRouter(prefix="/admin", tags=["Admin"])

# ============================================================================
# SCHEMAS FOR USER MANAGEMENT
# ============================================================================

class UserCreate(BaseModel):
    username: str
    password: str
    full_name: str
    role: str  # admin, user_cpns, user_polri, user_mixed
    test_type: str  # cpns, polri, mixed
    tier: str  # free, basic, premium
    
    class Config:
        json_schema_extra = {
            "example": {
                "username": "user123",
                "password": "password123",
                "full_name": "John Doe",
                "role": "user_cpns",
                "test_type": "cpns",
                "tier": "free"
            }
        }

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[str] = None
    test_type: Optional[str] = None
    tier: Optional[str] = None
    is_active: Optional[bool] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "tier": "premium",
                "is_active": True
            }
        }

# ============================================================================
# DASHBOARD STATISTICS
# ============================================================================

@router.get("/dashboard")
def get_dashboard_stats(
    current_user: User = Depends(admin_required),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive dashboard statistics (Admin only)
    
    Returns:
    - User statistics
    - Question statistics
    - Session statistics
    - System health metrics
    """
    
    # User stats
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()
    
    # Count by tier
    tier_breakdown = db.query(
        User.tier,
        func.count(User.user_id)
    ).group_by(User.tier).all()
    
    tier_stats = {tier: count for tier, count in tier_breakdown}
    
    # Count by test type
    test_type_breakdown = db.query(
        User.test_type,
        func.count(User.user_id)
    ).group_by(User.test_type).all()
    
    test_type_stats = {tt: count for tt, count in test_type_breakdown}
    
    # Count by role
    role_breakdown = db.query(
        User.role,
        func.count(User.user_id)
    ).group_by(User.role).all()
    
    role_stats = {role: count for role, count in role_breakdown}
    
    # Question stats
    total_questions = db.query(Question).count()
    questions_by_category = db.query(
        Question.test_category,
        func.count(Question.question_id)
    ).group_by(Question.test_category).all()
    
    category_stats = {cat: count for cat, count in questions_by_category}
    
    questions_by_difficulty = db.query(
        Question.difficulty,
        func.count(Question.question_id)
    ).group_by(Question.difficulty).all()
    
    difficulty_stats = {diff: count for diff, count in questions_by_difficulty}
    
    # Session stats
    total_sessions = db.query(QuestionSession).count()
    completed_sessions = db.query(QuestionSession).filter(
        QuestionSession.status == 'completed'
    ).count()
    active_sessions = db.query(QuestionSession).filter(
        QuestionSession.status == 'in_progress'
    ).count()
    
    # Sessions by mode
    mode_breakdown = db.query(
        QuestionSession.mode,
        func.count(QuestionSession.session_id)
    ).group_by(QuestionSession.mode).all()
    
    mode_stats = {mode if mode else 'practice': count for mode, count in mode_breakdown}
    
    # Recent activity (last 7 days)
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    recent_sessions = db.query(QuestionSession).filter(
        QuestionSession.created_at >= week_ago
    ).count()
    
    recent_users = db.query(User).filter(
        User.user_id.in_(
            db.query(QuestionSession.user_id).filter(
                QuestionSession.created_at >= week_ago
            ).distinct()
        )
    ).count()
    
    # Calculate completion rate
    completion_rate = (completed_sessions / total_sessions * 100) if total_sessions > 0 else 0
    
    return {
        "users": {
            "total": total_users,
            "active": active_users,
            "inactive": total_users - active_users,
            "by_tier": tier_stats,
            "by_test_type": test_type_stats,
            "by_role": role_stats,
            "new_this_week": recent_users
        },
        "questions": {
            "total": total_questions,
            "by_category": category_stats,
            "by_difficulty": difficulty_stats
        },
        "sessions": {
            "total": total_sessions,
            "completed": completed_sessions,
            "active": active_sessions,
            "by_mode": mode_stats,
            "this_week": recent_sessions,
            "completion_rate": round(completion_rate, 2)
        },
        "generated_at": datetime.now(timezone.utc)
    }

# ============================================================================
# SYSTEM STATISTICS
# ============================================================================

@router.get("/statistics")
def get_system_statistics(
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(admin_required),
    db: Session = Depends(get_db)
):
    """
    Get detailed system statistics (Admin only)
    
    Query Parameters:
    - days: Number of days to analyze (default: 30)
    
    Returns:
    - Usage patterns
    - Performance metrics
    - Growth trends
    """
    
    date_threshold = datetime.now(timezone.utc) - timedelta(days=days)
    
    # Daily sessions trend
    daily_sessions = db.query(
        func.date(QuestionSession.created_at).label('date'),
        func.count(QuestionSession.session_id).label('count')
    ).filter(
        QuestionSession.created_at >= date_threshold
    ).group_by(
        func.date(QuestionSession.created_at)
    ).order_by('date').all()
    
    # Most active users (top 10)
    top_users = db.query(
        UserProgress.user_id,
        UserProgress.total_sessions,
        UserProgress.overall_accuracy
    ).order_by(
        desc(UserProgress.total_sessions)
    ).limit(10).all()
    
    top_users_data = []
    for user_id, sessions, accuracy in top_users:
        user = db.query(User).filter(User.user_id == user_id).first()
        top_users_data.append({
            "user_id": user_id,
            "username": user.username if user else "Unknown",
            "full_name": user.full_name if user else "Unknown",
            "total_sessions": sessions,
            "overall_accuracy": accuracy
        })
    
    # Most used questions
    popular_questions = db.query(
        Question.question_id,
        Question.subject,
        Question.usage_count,
        Question.correct_rate
    ).order_by(
        desc(Question.usage_count)
    ).limit(10).all()
    
    popular_q_data = [
        {
            "question_id": q_id,
            "subject": subject,
            "usage_count": usage,
            "correct_rate": rate
        }
        for q_id, subject, usage, rate in popular_questions
    ]
    
    # Average session score
    completed_sessions = db.query(QuestionSession).filter(
        QuestionSession.status == 'completed',
        QuestionSession.created_at >= date_threshold,
        QuestionSession.score != None
    ).all()
    
    avg_score = 0.0
    if completed_sessions:
        scores = [s.score for s in completed_sessions if s.score is not None]
        avg_score = sum(scores) / len(scores) if scores else 0.0
    
    return {
        "period_days": days,
        "daily_sessions": [
            {"date": str(date), "count": count}
            for date, count in daily_sessions
        ],
        "average_score": round(avg_score, 2),
        "top_users": top_users_data,
        "popular_questions": popular_q_data
    }

# ============================================================================
# AUDIT LOGS
# ============================================================================

@router.get("/audit-logs", response_model=AuditLogList)
def get_audit_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    action: Optional[str] = None,
    user_id: Optional[str] = None,
    success: Optional[bool] = None,
    current_user: User = Depends(admin_required),
    db: Session = Depends(get_db)
):
    """
    Get system audit logs (Admin only)
    
    Query Parameters:
    - skip: Pagination offset
    - limit: Number of results
    - action: Filter by action type
    - user_id: Filter by user ID
    - success: Filter by success status
    """
    
    query = db.query(AuditLog)
    
    # Apply filters
    if action:
        query = query.filter(AuditLog.action == action)
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    if success is not None:
        query = query.filter(AuditLog.success == success)
    
    # Order by timestamp descending
    query = query.order_by(desc(AuditLog.timestamp))
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    logs = query.offset(skip).limit(limit).all()
    
    logs_data = [
        {
            "log_id": log.log_id,
            "action": log.action,
            "user_id": log.user_id,
            "performed_by": log.performed_by,
            "details": log.details,
            "ip_address": log.ip_address,
            "success": log.success,
            "timestamp": log.timestamp
        }
        for log in logs
    ]
    
    return {
        "logs": logs_data,
        "total": total,
        "skip": skip,
        "limit": limit
    }

# ============================================================================
# USER MANAGEMENT (NEW)
# ============================================================================

@router.get("/users")
def get_all_users(
    skip: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(100, ge=1, le=100, description="Number of results"),
    search: Optional[str] = Query(None, description="Search username or name"),
    role: Optional[str] = Query(None, description="Filter by role"),
    tier: Optional[str] = Query(None, description="Filter by tier"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    current_user: User = Depends(admin_required),
    db: Session = Depends(get_db)
):
    """
    Get all users with filters (Admin only)
    
    Query Parameters:
    - skip: Pagination offset
    - limit: Number of results (max 100)
    - search: Search in username or full_name
    - role: Filter by role (admin, user_cpns, user_polri, user_mixed)
    - tier: Filter by tier (free, basic, premium)
    - is_active: Filter by active status
    """
    try:
        query = db.query(User)
        
        # Apply filters
        if search:
            query = query.filter(
                (User.username.ilike(f"%{search}%")) |
                (User.full_name.ilike(f"%{search}%"))
            )
        
        if role:
            query = query.filter(User.role == role)
        
        if tier:
            query = query.filter(User.tier == tier)
        
        if is_active is not None:
            query = query.filter(User.is_active == is_active)
        
        # Get total count
        total = query.count()
        
        # Get users
        users = query.order_by(desc(User.created_at)).offset(skip).limit(limit).all()
        
        return {
            'status': 'success',
            'data': {
                'total': total,
                'users': [
                    {
                        'user_id': u.user_id,
                        'username': u.username,
                        'full_name': u.full_name,
                        'role': u.role,
                        'test_type': u.test_type,
                        'tier': u.tier,
                        'is_active': u.is_active,
                        'created_at': u.created_at.isoformat() if u.created_at else None,
                        'last_login': u.last_login.isoformat() if u.last_login else None,
                        'subscription_end': u.subscription_end.isoformat() if u.subscription_end else None
                    }
                    for u in users
                ]
            }
        }
        
    except Exception as e:
        print(f"❌ Error getting users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/users/{user_id}")
def get_user_detail(
    user_id: str,
    current_user: User = Depends(admin_required),
    db: Session = Depends(get_db)
):
    """
    Get detailed user information (Admin only)
    """
    try:
        user = db.query(User).filter(User.user_id == user_id).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Get user statistics
        total_sessions = db.query(func.count(QuestionSession.session_id)).filter(
            QuestionSession.user_id == user_id,
            QuestionSession.status == 'completed'
        ).scalar() or 0
        
        avg_score = db.query(func.avg(QuestionSession.score)).filter(
            QuestionSession.user_id == user_id,
            QuestionSession.status == 'completed',
            QuestionSession.score.isnot(None)
        ).scalar() or 0
        
        # Get progress
        progress = db.query(UserProgress).filter(
            UserProgress.user_id == user_id
        ).first()
        
        return {
            'status': 'success',
            'data': {
                'user': {
                    'user_id': user.user_id,
                    'username': user.username,
                    'full_name': user.full_name,
                    'role': user.role,
                    'test_type': user.test_type,
                    'tier': user.tier,
                    'is_active': user.is_active,
                    'created_at': user.created_at.isoformat() if user.created_at else None,
                    'last_login': user.last_login.isoformat() if user.last_login else None,
                    'subscription_start': user.subscription_start.isoformat() if user.subscription_start else None,
                    'subscription_end': user.subscription_end.isoformat() if user.subscription_end else None
                },
                'statistics': {
                    'total_sessions': total_sessions,
                    'average_score': round(avg_score, 2),
                    'total_questions': progress.total_questions if progress else 0,
                    'total_correct': progress.total_correct if progress else 0,
                    'overall_accuracy': round(progress.overall_accuracy, 2) if progress else 0
                }
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error getting user detail: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/users")
def create_user(
    user_data: UserCreate,
    current_user: User = Depends(admin_required),
    db: Session = Depends(get_db)
):
    """
    Create new user (Admin only)
    """
    try:
        # Check if username exists
        existing = db.query(User).filter(User.username == user_data.username).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already exists"
            )
        
        # Validate role
        valid_roles = ['admin', 'user_cpns', 'user_polri', 'user_mixed']
        if user_data.role not in valid_roles:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role. Must be one of: {', '.join(valid_roles)}"
            )
        
        # Validate test_type
        valid_test_types = ['cpns', 'polri', 'mixed']
        if user_data.test_type not in valid_test_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid test_type. Must be one of: {', '.join(valid_test_types)}"
            )
        
        # Validate tier
        valid_tiers = ['free', 'basic', 'premium']
        if user_data.tier not in valid_tiers:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid tier. Must be one of: {', '.join(valid_tiers)}"
            )
        
        # Create user
        new_user = User(
            username=user_data.username,
            hashed_password=get_password_hash(user_data.password),
            full_name=user_data.full_name,
            role=user_data.role,
            test_type=user_data.test_type,
            tier=user_data.tier,
            is_active=True,
            created_at=datetime.now(timezone.utc)
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        # Log action
        log = AuditLog(
            action='user_created',
            user_id=new_user.user_id,
            performed_by=current_user.user_id,
            details={
                'username': new_user.username,
                'role': new_user.role,
                'tier': new_user.tier
            },
            timestamp=datetime.now(timezone.utc),
            success=True
        )
        db.add(log)
        db.commit()
        
        return {
            'status': 'success',
            'message': 'User created successfully',
            'data': {
                'user_id': new_user.user_id,
                'username': new_user.username,
                'role': new_user.role,
                'tier': new_user.tier
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"❌ Error creating user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.put("/users/{user_id}")
def update_user(
    user_id: str,
    user_data: UserUpdate,
    current_user: User = Depends(admin_required),
    db: Session = Depends(get_db)
):
    """
    Update user information (Admin only)
    """
    try:
        user = db.query(User).filter(User.user_id == user_id).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Update fields
        if user_data.full_name is not None:
            user.full_name = user_data.full_name
        
        if user_data.role is not None:
            valid_roles = ['admin', 'user_cpns', 'user_polri', 'user_mixed']
            if user_data.role not in valid_roles:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid role. Must be one of: {', '.join(valid_roles)}"
                )
            user.role = user_data.role
        
        if user_data.test_type is not None:
            valid_test_types = ['cpns', 'polri', 'mixed']
            if user_data.test_type not in valid_test_types:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid test_type. Must be one of: {', '.join(valid_test_types)}"
                )
            user.test_type = user_data.test_type
        
        if user_data.tier is not None:
            valid_tiers = ['free', 'basic', 'premium']
            if user_data.tier not in valid_tiers:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid tier. Must be one of: {', '.join(valid_tiers)}"
                )
            user.tier = user_data.tier
        
        if user_data.is_active is not None:
            user.is_active = user_data.is_active
        
        db.commit()
        db.refresh(user)
        
        # Log action
        log = AuditLog(
            action='user_updated',
            user_id=user.user_id,
            performed_by=current_user.user_id,
            details=user_data.dict(exclude_unset=True),
            timestamp=datetime.now(timezone.utc),
            success=True
        )
        db.add(log)
        db.commit()
        
        return {
            'status': 'success',
            'message': 'User updated successfully',
            'data': {
                'user_id': user.user_id,
                'username': user.username,
                'role': user.role,
                'test_type': user.test_type,
                'tier': user.tier,
                'is_active': user.is_active
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"❌ Error updating user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.delete("/users/{user_id}")
def deactivate_user(
    user_id: str,
    current_user: User = Depends(admin_required),
    db: Session = Depends(get_db)
):
    """
    Deactivate user (soft delete) - Admin only
    """
    try:
        user = db.query(User).filter(User.user_id == user_id).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Don't allow deactivating yourself
        if user.user_id == current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot deactivate your own account"
            )
        
        user.is_active = False
        db.commit()
        
        # Log action
        log = AuditLog(
            action='user_deactivated',
            user_id=user.user_id,
            performed_by=current_user.user_id,
            details={'username': user.username},
            timestamp=datetime.now(timezone.utc),
            success=True
        )
        db.add(log)
        db.commit()
        
        return {
            'status': 'success',
            'message': 'User deactivated successfully'
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"❌ Error deactivating user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )