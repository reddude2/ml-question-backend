"""
Review API Router
Handles review sessions and statistics
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict
from pydantic import BaseModel

from database import get_db
from core.session_manager import SessionManager
from core.smart_question_selector import SmartQuestionSelector
from core.dependencies import get_current_user
from models import User

router = APIRouter(prefix="/api/review", tags=["review"])

# ============================================================================
# RESPONSE MODELS
# ============================================================================

class ReviewableSessionResponse(BaseModel):
    """Reviewable session info"""
    session_id: str
    completed_at: str
    test_category: str
    subject: str
    session_type: str
    total_questions: int
    correct_count: int
    score: float
    can_review: bool

class ReviewStatsResponse(BaseModel):
    """Review statistics"""
    total_sessions_completed: int
    total_reviewable: int
    most_recent_review: Dict = None

# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("/sessions", response_model=List[Dict])
async def get_reviewable_sessions(
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get list of sessions that can be reviewed
    
    - **limit**: Maximum sessions to return (default: 20)
    
    Returns list of completed sessions available for review
    """
    try:
        selector = SmartQuestionSelector(db_session=db)
        
        sessions = selector.get_user_session_history(
            user_id=current_user.user_id,
            limit=limit
        )
        
        return sessions
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/{session_id}/start", response_model=Dict)
async def start_review_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Start a review session
    
    - **session_id**: ID of completed session to review
    
    Returns new review session with same questions and previous answers
    """
    try:
        manager = SessionManager(db_session=db)
        
        result = manager.create_review_session(
            user_id=current_user.user_id,
            original_session_id=session_id
        )
        
        if not result.get('success'):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result.get('error', 'Session not found')
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/stats", response_model=Dict)
async def get_review_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get review statistics
    
    Returns statistics about completed and reviewable sessions
    """
    try:
        selector = SmartQuestionSelector(db_session=db)
        
        # Get all completed sessions
        all_sessions = selector.get_user_session_history(
            user_id=current_user.user_id,
            limit=100
        )
        
        stats = {
            'total_sessions_completed': len(all_sessions),
            'total_reviewable': len([s for s in all_sessions if s.get('can_review')]),
            'most_recent_session': all_sessions[0] if all_sessions else None,
            'sessions_by_subject': {}
        }
        
        # Group by subject
        for session in all_sessions:
            subject = session.get('subject', 'unknown')
            if subject not in stats['sessions_by_subject']:
                stats['sessions_by_subject'][subject] = {
                    'count': 0,
                    'avg_score': 0,
                    'total_score': 0
                }
            
            stats['sessions_by_subject'][subject]['count'] += 1
            stats['sessions_by_subject'][subject]['total_score'] += session.get('score', 0)
            stats['sessions_by_subject'][subject]['avg_score'] = (
                stats['sessions_by_subject'][subject]['total_score'] / 
                stats['sessions_by_subject'][subject]['count']
            )
        
        return stats
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )