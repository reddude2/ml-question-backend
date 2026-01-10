"""
FastAPI Dependencies
Reusable dependencies for routes

SECURITY LAYERS:
1. Authentication - verify token & get user
2. Authorization - check roles & tiers
3. Access Control - validate test type access

ROLES:
- admin: Full access + user management
- user_cpns: CPNS questions only
- user_polri: POLRI questions only  
- user_mixed: Both CPNS & POLRI

TIERS:
- free: No exam mode, no explanations
- basic: Has explanations, no exam mode
- premium: Full access (exam mode + explanations)
"""

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import JWTError
from database import get_db
from models import User, get_role_access_level, get_tier_features
from core.security import verify_token

security = HTTPBearer()

# ============================================================================
# AUTHENTICATION - Get Current User
# ============================================================================

def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Get current authenticated user from JWT token
    
    Works in TWO modes:
    1. With middleware: Uses request.state.user_id (faster)
    2. Without middleware: Verifies token directly (fallback)
    
    This ensures compatibility whether middleware is enabled or not.
    
    Raises:
        HTTPException: If token is invalid or user not found
    """
    user_id = None
    
    try:
        # MODE 1: Try to get user_id from middleware (if available)
        # Middleware sets request.state.user_id after verifying token
        if hasattr(request, 'state') and hasattr(request.state, 'user_id'):
            user_id = request.state.user_id
        
        # MODE 2: Fallback - verify token directly
        # This ensures it works even if middleware is disabled
        if not user_id:
            token = credentials.credentials
            payload = verify_token(token)
            user_id = payload.get("sub")
        
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
            
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )
    
    # Get user from database
    user = db.query(User).filter(User.user_id == user_id).first()
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    return user

def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Alias for get_current_user (for clarity in code)
    Explicitly shows we want an active user
    """
    return current_user

# ============================================================================
# ROLE-BASED ACCESS CONTROL
# ============================================================================

def admin_required(current_user: User = Depends(get_current_user)) -> User:
    """
    Require admin role
    
    Usage:
        @router.get("/admin-only")
        def admin_endpoint(current_user: User = Depends(admin_required)):
            # Only admins can access this
    
    Raises:
        HTTPException: If user is not admin
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user

def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """
    Alias for admin_required (for consistency with other require_* functions)
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user

# ============================================================================
# TIER-BASED ACCESS CONTROL
# ============================================================================

def require_premium(current_user: User = Depends(get_current_user)) -> User:
    """
    Require PREMIUM tier access
    
    Features requiring premium:
    - Exam mode (mixed subjects)
    - Advanced statistics
    - Priority support
    
    Usage:
        @router.post("/exam/create")
        def create_exam(current_user: User = Depends(require_premium)):
            # Only premium users can create exam sessions
    
    Raises:
        HTTPException: If user is not premium tier
    """
    if current_user.tier != 'premium':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "premium_required",
                "message": f"This feature requires PREMIUM tier",
                "current_tier": current_user.tier,
                "required_tier": "premium",
                "upgrade_message": "Upgrade to Premium to access exam mode and advanced features"
            }
        )
    return current_user

def require_basic_or_premium(current_user: User = Depends(get_current_user)) -> User:
    """
    Require BASIC or PREMIUM tier access
    
    Features requiring basic/premium:
    - Question explanations
    - Detailed feedback
    - Answer breakdowns
    
    Usage:
        @router.get("/questions/{id}/explanation")
        def get_explanation(current_user: User = Depends(require_basic_or_premium)):
            # Only basic/premium users get explanations
    
    Raises:
        HTTPException: If user is free tier
    """
    if current_user.tier not in ['basic', 'premium']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "basic_required",
                "message": f"This feature requires BASIC or PREMIUM tier",
                "current_tier": current_user.tier,
                "required_tier": "basic",
                "upgrade_message": "Upgrade to Basic or Premium to see explanations"
            }
        )
    return current_user

# ============================================================================
# TEST TYPE ACCESS CONTROL (FIXED)
# ============================================================================

def check_test_type_access(user: User, test_category: str) -> bool:
    """
    Check if user can access this test category
    
    Access rules (UPDATED):
    - admin: Can access EVERYTHING (CPNS + POLRI) - NO RESTRICTIONS
    - user_mixed OR test_type='mixed': Can access both CPNS & POLRI
    - user_cpns OR test_type='cpns': Can only access CPNS
    - user_polri OR test_type='polri': Can only access POLRI
    
    Args:
        user: Current user
        test_category: 'cpns' or 'polri'
    
    Returns:
        bool: True if user has access, False otherwise
    """
    # ADMIN CAN ACCESS EVERYTHING - NO RESTRICTIONS!
    if user.role == 'admin':
        return True
    
    test_category_lower = test_category.lower()
    
    # user_mixed OR test_type='mixed' can access both
    if user.role == 'user_mixed' or user.test_type == 'mixed':
        return True
    
    # Check both role AND test_type for CPNS (OR logic)
    if test_category_lower == 'cpns':
        if user.role == 'user_cpns' or user.test_type == 'cpns':
            return True
    
    # Check both role AND test_type for POLRI (OR logic)
    if test_category_lower == 'polri':
        if user.role == 'user_polri' or user.test_type == 'polri':
            return True
    
    return False

def validate_test_access(user: User, test_category: str):
    """
    Validate test type access and raise exception if denied
    
    Usage:
        validate_test_access(current_user, 'cpns')
        # If user doesn't have access, HTTPException is raised
        # If user has access, function returns normally
    
    Args:
        user: Current user
        test_category: 'cpns' or 'polri'
    
    Raises:
        HTTPException: If user doesn't have access to this test category
    """
    if not check_test_type_access(user, test_category):
        # Map role to readable access description
        access_map = {
            'admin': 'All categories (CPNS & POLRI)',
            'user_cpns': 'CPNS only',
            'user_polri': 'POLRI only',
            'user_mixed': 'Both CPNS & POLRI'
        }
        
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "access_denied",
                "message": f"You don't have access to {test_category.upper()} questions",
                "your_role": user.role,
                "your_test_type": user.test_type,
                "your_access": access_map.get(user.role, 'None'),
                "requested_category": test_category.upper(),
                "contact_admin": "Contact admin to change your access level"
            }
        )

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_user_tier_features(user: User) -> dict:
    """
    Get features available for user's tier
    
    Returns dict with feature flags:
    - can_practice: Can do practice sessions
    - can_review: Can review past sessions
    - can_exam_mode: Can do exam mode (mixed subjects)
    - has_explanations: Can see question explanations
    - has_statistics: Can see detailed statistics
    - max_questions_per_session: Max questions allowed
    
    Usage:
        features = get_user_tier_features(current_user)
        if not features['can_exam_mode']:
            # Show upgrade prompt
    """
    return get_tier_features(user.tier)

def get_user_role_access(user: User) -> dict:
    """
    Get access permissions for user's role
    
    Returns dict with permission flags:
    - can_access_cpns: Can access CPNS questions
    - can_access_polri: Can access POLRI questions
    - can_manage_users: Can manage other users
    - can_view_all_data: Can view all users' data
    - can_upload_materials: Can upload materials
    
    Usage:
        access = get_user_role_access(current_user)
        if not access['can_access_cpns']:
            # Show access denied message
    """
    return get_role_access_level(user.role)

def filter_explanation_by_tier(question: dict, user: User) -> dict:
    """
    Filter question explanation based on user tier
    
    FREE tier: Explanation is removed (set to None)
    BASIC tier: Explanation is included
    PREMIUM tier: Explanation is included
    
    Args:
        question: Question dict with 'explanation' field
        user: Current user
    
    Returns:
        dict: Question with explanation filtered based on tier
    
    Usage:
        question = filter_explanation_by_tier(question_data, current_user)
        # If user is free tier, question['explanation'] will be None
    """
    if user.tier == 'free':
        # Remove explanation for free users
        question['explanation'] = None
    
    return question

def check_question_limit(user: User, requested_count: int) -> bool:
    """
    Check if user can request this many questions
    
    Limits by tier:
    - FREE: max 10 questions per session
    - BASIC: max 50 questions per session
    - PREMIUM: max 200 questions per session
    
    Args:
        user: Current user
        requested_count: Number of questions requested
    
    Returns:
        bool: True if within limit, False if exceeds limit
    """
    features = get_user_tier_features(user)
    max_allowed = features.get('max_questions_per_session', 10)
    
    return requested_count <= max_allowed

def validate_question_limit(user: User, requested_count: int):
    """
    Validate question count limit and raise exception if exceeded
    
    Usage:
        validate_question_limit(current_user, question_count)
        # If exceeds limit, HTTPException is raised
    
    Raises:
        HTTPException: If requested count exceeds tier limit
    """
    features = get_user_tier_features(user)
    max_allowed = features.get('max_questions_per_session', 10)
    
    if requested_count > max_allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "question_limit_exceeded",
                "message": f"Your tier allows maximum {max_allowed} questions per session",
                "current_tier": user.tier,
                "requested": requested_count,
                "max_allowed": max_allowed,
                "upgrade_message": "Upgrade to increase your question limit"
            }
        )

# ============================================================================
# COMBINED VALIDATORS
# ============================================================================

def validate_session_access(
    user: User,
    test_category: str,
    question_count: int,
    mode: str = 'practice'
):
    """
    Combined validator for session creation
    Checks:
    1. Test category access (based on role)
    2. Question count limit (based on tier)
    3. Exam mode access (premium only)
    
    Usage:
        validate_session_access(
            current_user,
            test_category='cpns',
            question_count=50,
            mode='exam'
        )
    
    Raises:
        HTTPException: If any validation fails
    """
    # Check test category access
    validate_test_access(user, test_category)
    
    # Check question limit
    validate_question_limit(user, question_count)
    
    # Check exam mode access (premium only)
    if mode == 'exam' and user.tier != 'premium':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "exam_mode_premium_only",
                "message": "Exam mode is only available for Premium users",
                "current_tier": user.tier,
                "required_tier": "premium",
                "upgrade_message": "Upgrade to Premium to access exam mode"
            }
        )