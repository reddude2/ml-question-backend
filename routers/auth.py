"""
Authentication Router
Login, logout, token verification, password change
WITH FLAT RESPONSE STRUCTURE FOR DESKTOP APP COMPATIBILITY
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from database import get_db
from models import User, AuditLog
from schemas import PasswordChange
from core.security import verify_password, create_access_token, hash_password
from core.dependencies import get_current_user
from datetime import datetime, timezone
import traceback as tb

router = APIRouter(prefix="/auth", tags=["Authentication"])

# ============================================================================
# LOGIN ENDPOINT - FIXED FOR DESKTOP APP
# ============================================================================

@router.post("/login")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    User login endpoint - OAuth2 compatible
    Returns FLAT structure (NOT nested) for desktop app compatibility
    """
    
    try:
        print(f"\n{'='*70}")
        print(f"🔐 LOGIN ATTEMPT")
        print(f"{'='*70}")
        print(f"Username: {form_data.username}")
        
        # Get user by username
        user = db.query(User).filter(User.username == form_data.username).first()
        
        if not user:
            print(f"❌ User not found: {form_data.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        print(f"✅ User found in database")
        print(f"   User ID: {user.user_id}")
        print(f"   Username: {user.username}")
        print(f"   Tier in DB: {user.tier}")
        print(f"   Role in DB: {user.role}")
        print(f"   Branch in DB: {user.branch_access}")
        
        # Verify password
        if not verify_password(form_data.password, user.hashed_password):
            print(f"❌ Invalid password for user: {form_data.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        print(f"✅ Password verified")
        
        # Check if user is active
        if not user.is_active:
            print(f"❌ User account is inactive")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive"
            )
        
        print(f"✅ User account is active")
        
        # Check subscription (optional - skip if not using subscriptions)
        if user.subscription_end:
            if user.subscription_end < datetime.now(timezone.utc):
                print(f"❌ Subscription expired")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Subscription has expired"
                )
        
        # Create access token
        token = create_access_token(data={
            "sub": user.user_id,
            "username": user.username,
            "role": user.role,
            "tier": user.tier
        })
        
        print(f"✅ Access token created")
        
        # Calculate days remaining (if using subscriptions)
        days_remaining = None
        if user.subscription_end:
            delta = user.subscription_end - datetime.now(timezone.utc)
            days_remaining = max(0, delta.days)
        
        # ====================================================================
        # CRITICAL: Return FLAT structure (NOT nested)
        # Desktop app expects: { access_token, tier, role, ... }
        # NOT: { access_token, user: { tier, role } }
        # ====================================================================
        
        response = {
            # OAuth2 standard fields
            'access_token': token,
            'token_type': 'bearer',
            
            # User data (FLAT - not nested!)
            'user_id': user.user_id,
            'username': user.username,
            'full_name': user.full_name or user.username,
            'role': user.role or 'user_cpns',
            'tier': user.tier or 'free',  # ← MUST BE AT ROOT LEVEL!
            'test_type': user.test_type or 'cpns',
            'branch_access': user.branch_access or 'cpns',
            'session_count': user.session_count or 0,
            'is_active': user.is_active,
            
            # Subscription info (optional)
            'subscription_end': user.subscription_end.isoformat() if user.subscription_end else None,
            'days_remaining': days_remaining
        }
        
        print(f"\n{'='*70}")
        print(f"✅✅✅ LOGIN SUCCESSFUL ✅✅✅")
        print(f"{'='*70}")
        print(f"Response structure (FLAT):")
        print(f"   access_token: {token[:30]}...")
        print(f"   user_id:      {response['user_id']}")
        print(f"   username:     {response['username']}")
        print(f"   tier:         {response['tier']} 💎")
        print(f"   role:         {response['role']} 👔")
        print(f"   branch:       {response['branch_access']} 🌿")
        print(f"   session_count: {response['session_count']}")
        print(f"{'='*70}\n")
        
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        print("\n" + "=" * 80)
        print("🔴 UNEXPECTED ERROR IN LOGIN:")
        print("=" * 80)
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {e}")
        print("\nFull traceback:")
        tb.print_exc()
        print("=" * 80 + "\n")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

# ============================================================================
# TOKEN VERIFICATION
# ============================================================================

@router.get("/verify")
def verify_token(current_user: User = Depends(get_current_user)):
    """Verify JWT token and get current user info"""
    
    print(f"🔍 Token verification for user: {current_user.username}")
    
    days_remaining = None
    is_expired = False
    
    if current_user.subscription_end:
        now = datetime.now(timezone.utc)
        delta = current_user.subscription_end - now
        days_remaining = max(0, delta.days)
        is_expired = delta.days < 0
    
    # Return FLAT structure
    return {
        "user_id": current_user.user_id,
        "username": current_user.username,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "tier": current_user.tier,  # ← FLAT!
        "test_type": current_user.test_type,
        "branch_access": current_user.branch_access,
        "session_count": current_user.session_count,
        "is_active": current_user.is_active,
        "subscription_start": current_user.subscription_start,
        "subscription_end": current_user.subscription_end,
        "days_remaining": days_remaining,
        "is_expired": is_expired
    }

# ============================================================================
# GET CURRENT USER
# ============================================================================

@router.get("/me")
def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current authenticated user information"""
    
    print(f"👤 Getting user info for: {current_user.username}")
    
    days_remaining = None
    if current_user.subscription_end:
        delta = current_user.subscription_end - datetime.now(timezone.utc)
        days_remaining = max(0, delta.days)
    
    return {
        "user_id": current_user.user_id,
        "username": current_user.username,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "tier": current_user.tier,
        "test_type": current_user.test_type,
        "branch_access": current_user.branch_access,
        "session_count": current_user.session_count,
        "is_active": current_user.is_active,
        "subscription_end": current_user.subscription_end.isoformat() if current_user.subscription_end else None,
        "days_remaining": days_remaining
    }

# ============================================================================
# PASSWORD CHANGE
# ============================================================================

@router.post("/change-password")
def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Change user password"""
    
    print(f"🔑 Password change request for user: {current_user.username}")
    
    # Verify old password
    if not verify_password(password_data.old_password, current_user.hashed_password):
        print(f"❌ Old password incorrect")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Old password is incorrect"
        )
    
    # Check new password is different
    if verify_password(password_data.new_password, current_user.hashed_password):
        print(f"❌ New password same as old")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from old password"
        )
    
    # Update password
    current_user.hashed_password = hash_password(password_data.new_password)
    db.commit()
    
    print(f"✅ Password changed successfully for user: {current_user.username}")
    
    return {
        "status": "success",
        "message": "Password changed successfully",
        "data": None
    }

# ============================================================================
# LOGOUT
# ============================================================================

@router.post("/logout")
def logout(current_user: User = Depends(get_current_user)):
    """Logout user (client should discard token)"""
    
    print(f"🚪 User logged out: {current_user.username}")
    
    return {
        "status": "success",
        "message": "Logged out successfully",
        "data": None
    }