"""
Tier Check Middleware
Enforce tier-based limitations
"""

from fastapi import HTTPException, status
from models import User, QuestionSession
from config import TIER_LIMITS
from datetime import datetime, timezone
from database import SessionLocal

def check_tier_limits(user: User, action: str, **kwargs) -> dict:
    """Check if user can perform action based on tier limits"""
    tier = user.tier
    tier_config = TIER_LIMITS.get(tier, TIER_LIMITS["free"])
    
    if action == "create_session":
        question_count = kwargs.get("question_count", 0)
        max_questions = tier_config["max_questions_per_session"]
        
        if question_count > max_questions:
            return {
                "allowed": False,
                "message": f"Tier {tier} maksimal {max_questions} soal per sesi",
                "remaining": 0
            }
        
        max_daily = tier_config["max_sessions_per_day"]
        
        if max_daily != "unlimited":
            db = SessionLocal()
            try:
                today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
                today_sessions = db.query(QuestionSession).filter(
                    QuestionSession.user_id == user.user_id,
                    QuestionSession.created_at >= today_start
                ).count()
                
                if today_sessions >= max_daily:
                    return {
                        "allowed": False,
                        "message": f"Tier {tier} sudah mencapai limit {max_daily} sesi per hari",
                        "remaining": 0
                    }
                
                remaining = max_daily - today_sessions
            finally:
                db.close()
        else:
            remaining = None
        
        return {"allowed": True, "message": "OK", "remaining": remaining}
    
    return {"allowed": True, "message": "Unknown action", "remaining": None}

def enforce_tier_limit(user: User, action: str, **kwargs):
    """Enforce tier limit - raise HTTPException if not allowed"""
    result = check_tier_limits(user, action, **kwargs)
    if not result["allowed"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=result["message"]
        )
    return result