"""
Users Router
User management endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from database import get_db
from models import User, UserProgress
from schemas import UserResponse, UserCreate, UserUpdate, UserList, SuccessResponse
from core.security import hash_password, generate_password
from core.dependencies import get_current_user, admin_required
from core.access_control import validate_test_type
from datetime import datetime, timezone, timedelta
from typing import Optional

router = APIRouter(prefix="/users", tags=["Users"])

@router.get("/me", response_model=UserResponse)
def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    days_remaining = None
    is_expired = False
    
    if current_user.subscription_end:
        delta = current_user.subscription_end - datetime.now(timezone.utc)
        days_remaining = max(0, delta.days)
        is_expired = delta.days < 0
    
    return {
        "user_id": current_user.user_id,
        "username": current_user.username,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "test_type": current_user.test_type,
        "tier": current_user.tier,
        "is_active": current_user.is_active,
        "subscription_start": current_user.subscription_start,
        "subscription_end": current_user.subscription_end,
        "days_remaining": days_remaining,
        "is_expired": is_expired
    }

@router.get("/", response_model=UserList)
def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    search: Optional[str] = None,
    test_type: Optional[str] = None,
    tier: Optional[str] = None,
    is_active: Optional[bool] = None,
    current_user: User = Depends(admin_required),
    db: Session = Depends(get_db)
):
    """List all users (Admin only)"""
    query = db.query(User)
    
    if search:
        query = query.filter(
            (User.username.ilike(f"%{search}%")) |
            (User.full_name.ilike(f"%{search}%"))
        )
    
    if test_type:
        query = query.filter(User.test_type == test_type)
    
    if tier:
        query = query.filter(User.tier == tier)
    
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    
    total = query.count()
    users = query.offset(skip).limit(limit).all()
    
    users_data = []
    for user in users:
        days_remaining = None
        if user.subscription_end:
            delta = user.subscription_end - datetime.now(timezone.utc)
            days_remaining = max(0, delta.days)
        
        users_data.append({
            "user_id": user.user_id,
            "username": user.username,
            "full_name": user.full_name,
            "role": user.role,
            "test_type": user.test_type,
            "tier": user.tier,
            "is_active": user.is_active,
            "subscription_end": user.subscription_end,
            "days_remaining": days_remaining
        })
    
    return {
        "users": users_data,
        "total": total,
        "skip": skip,
        "limit": limit
    }

@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: str,
    current_user: User = Depends(admin_required),
    db: Session = Depends(get_db)
):
    """Get user by ID (Admin only)"""
    user = db.query(User).filter(User.user_id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User tidak ditemukan"
        )
    
    days_remaining = None
    is_expired = False
    
    if user.subscription_end:
        delta = user.subscription_end - datetime.now(timezone.utc)
        days_remaining = max(0, delta.days)
        is_expired = delta.days < 0
    
    return {
        "user_id": user.user_id,
        "username": user.username,
        "full_name": user.full_name,
        "role": user.role,
        "test_type": user.test_type,
        "tier": user.tier,
        "is_active": user.is_active,
        "subscription_start": user.subscription_start,
        "subscription_end": user.subscription_end,
        "days_remaining": days_remaining,
        "is_expired": is_expired
    }

@router.post("/", status_code=status.HTTP_201_CREATED)
def create_user(
    user_data: UserCreate,
    current_user: User = Depends(admin_required),
    db: Session = Depends(get_db)
):
    """Create new user (Admin only)"""
    
    if db.query(User).filter(User.username == user_data.username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username sudah digunakan"
        )
    
    validate_test_type(user_data.test_type)
    
    password = user_data.password if user_data.password else generate_password()
    
    now = datetime.now(timezone.utc)
    new_user = User(
        username=user_data.username,
        hashed_password=hash_password(password),
        full_name=user_data.full_name,
        role=user_data.role,
        test_type=user_data.test_type,
        tier=user_data.tier,
        is_active=True,
        subscription_start=now,
        subscription_end=now + timedelta(days=user_data.subscription_days)
    )
    
    db.add(new_user)
    db.flush()
    
    progress = UserProgress(
        user_id=new_user.user_id,
        total_sessions=0,
        total_questions=0,
        total_correct=0,
        overall_accuracy=0.0,
        subject_stats={},
        last_activity=now
    )
    db.add(progress)
    db.commit()
    
    return {
        "status": "success",
        "message": "User berhasil dibuat",
        "data": {
            "user_id": new_user.user_id,
            "username": new_user.username,
            "password": password if not user_data.password else None
        }
    }

@router.put("/{user_id}")
def update_user(
    user_id: str,
    user_data: UserUpdate,
    current_user: User = Depends(admin_required),
    db: Session = Depends(get_db)
):
    """Update user (Admin only)"""
    user = db.query(User).filter(User.user_id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User tidak ditemukan"
        )
    
    if user_data.full_name is not None:
        user.full_name = user_data.full_name
    
    if user_data.test_type is not None:
        validate_test_type(user_data.test_type)
        user.test_type = user_data.test_type
    
    if user_data.tier is not None:
        user.tier = user_data.tier
    
    if user_data.is_active is not None:
        user.is_active = user_data.is_active
    
    if user_data.subscription_days is not None:
        now = datetime.now(timezone.utc)
        user.subscription_end = now + timedelta(days=user_data.subscription_days)
    
    db.commit()
    
    return {
        "status": "success",
        "message": "User berhasil diupdate",
        "data": {"user_id": user.user_id}
    }

@router.delete("/{user_id}")
def delete_user(
    user_id: str,
    current_user: User = Depends(admin_required),
    db: Session = Depends(get_db)
):
    """Delete user (Admin only)"""
    if user_id == current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tidak dapat menghapus user sendiri"
        )
    
    user = db.query(User).filter(User.user_id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User tidak ditemukan"
        )
    
    db.delete(user)
    db.commit()
    
    return {
        "status": "success",
        "message": "User berhasil dihapus",
        "data": None
    }