"""
Sessions Router (FULL VERSION)
Uses SessionManager for complex logic (Backfill, Smart Select)
✅ FIXED: Added 'submit_answer' endpoint (Fixes 405 Error)
✅ FIXED: Integrates with SessionManager for robust question selection
✅ FIXED: User Stats Calculation Logic (Fallback added)
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from database import get_db
from models import User, Question, QuestionSession, UserProgress, QuestionUsage
from schemas import (
    SessionCreate, SessionResponse, SessionList, 
    SessionSubmit, SessionResults
)
from core.dependencies import get_current_user
from middleware.tier_check import enforce_tier_limit
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List
from pydantic import BaseModel
import traceback

# Import core components
from core.session_manager import SessionManager
from core.smart_question_selector import SmartQuestionSelector

router = APIRouter(prefix="/sessions", tags=["Sessions"])

# ============================================================================
# NEW REQUEST/RESPONSE MODELS
# ============================================================================

class SubmitAnswerRequest(BaseModel):
    """Single answer submission"""
    question_id: str
    user_answer: str
    time_spent: Optional[int] = None

class AvailabilityResponse(BaseModel):
    """Question availability"""
    test_category: str
    subject: str
    total_available: int
    by_difficulty: Dict[str, int]
    can_create_session: bool

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def calculate_score(user_answers: dict, questions_data: list) -> dict:
    """Calculate score from user answers"""
    
    # Safety check if questions_data is None
    if not questions_data:
        questions_data = []

    total_questions = len(questions_data)
    answered = len(user_answers)
    correct = 0
    score = 0
    max_score = 0
    by_subject = {}
    
    for q_data in questions_data:
        q_id = q_data['question_id']
        subject = q_data.get('subject', 'unknown')
        
        # Initialize subject stats
        if subject not in by_subject:
            by_subject[subject] = {
                'total': 0,
                'answered': 0,
                'correct': 0,
                'score': 0,
                'max_score': 0
            }
        
        by_subject[subject]['total'] += 1
        
        # Check if question has answer_scores (TKP style) or correct_answer
        if q_data.get('answer_scores'):
            # TKP scoring
            max_score_for_q = max(q_data['answer_scores'].values())
            max_score += max_score_for_q
            by_subject[subject]['max_score'] += max_score_for_q
            
            if q_id in user_answers:
                by_subject[subject]['answered'] += 1
                user_answer = user_answers[q_id]
                points = q_data['answer_scores'].get(user_answer, 0)
                score += points
                by_subject[subject]['score'] += points
                
                # Consider "correct" if user got max points
                if points == max_score_for_q:
                    correct += 1
                    by_subject[subject]['correct'] += 1
        
        else:
            # Regular scoring (5 points per correct answer)
            max_score += 5
            by_subject[subject]['max_score'] += 5
            
            if q_id in user_answers:
                by_subject[subject]['answered'] += 1
                if user_answers[q_id] == q_data.get('correct_answer'):
                    correct += 1
                    score += 5
                    by_subject[subject]['correct'] += 1
                    by_subject[subject]['score'] += 5
    
    # Calculate percentages
    percentage = (score / max_score * 100) if max_score > 0 else 0
    
    for subject in by_subject:
        subj_max = by_subject[subject]['max_score']
        subj_score = by_subject[subject]['score']
        by_subject[subject]['percentage'] = (subj_score / subj_max * 100) if subj_max > 0 else 0
        
        subj_total = by_subject[subject]['total']
        subj_correct = by_subject[subject]['correct']
        by_subject[subject]['accuracy'] = (subj_correct / subj_total * 100) if subj_total > 0 else 0
    
    return {
        'total': total_questions,
        'answered': answered,
        'correct': correct,
        'score': score,
        'max_score': max_score,
        'percentage': round(percentage, 2),
        'by_subject': by_subject
    }

def update_user_progress(db: Session, user_id: str, session_results: dict):
    """Update user progress after session completion"""
    
    progress = db.query(UserProgress).filter(UserProgress.user_id == user_id).first()
    
    if not progress:
        progress = UserProgress(
            user_id=user_id,
            total_sessions=0,
            total_questions=0,
            total_correct=0,
            overall_accuracy=0.0,
            subject_stats={},
            last_activity=datetime.now(timezone.utc)
        )
        db.add(progress)
    
    # Initialize None values
    if progress.total_sessions is None:
        progress.total_sessions = 0
    if progress.total_questions is None:
        progress.total_questions = 0
    if progress.total_correct is None:
        progress.total_correct = 0
    if progress.subject_stats is None:
        progress.subject_stats = {}
    
    # Update totals
    progress.total_sessions += 1
    progress.total_questions += session_results['total']
    progress.total_correct += session_results['correct']
    
    # Update overall accuracy
    if progress.total_questions > 0:
        progress.overall_accuracy = round((progress.total_correct / progress.total_questions * 100), 2)
    
    # Update subject stats
    for subject, stats in session_results['by_subject'].items():
        if subject not in progress.subject_stats:
            progress.subject_stats[subject] = {
                'total': 0,
                'correct': 0,
                'accuracy': 0.0
            }
        
        progress.subject_stats[subject]['total'] += stats['total']
        progress.subject_stats[subject]['correct'] += stats['correct']
        
        subj_total = progress.subject_stats[subject]['total']
        subj_correct = progress.subject_stats[subject]['correct']
        progress.subject_stats[subject]['accuracy'] = round((subj_correct / subj_total * 100), 2)
    
    # Mark as modified for JSONB field
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(progress, "subject_stats")
    
    progress.last_activity = datetime.now(timezone.utc)
    progress.updated_at = datetime.now(timezone.utc)
    
    db.commit()

# ============================================================================
# CHECK AVAILABILITY (NEW)
# ============================================================================

@router.get("/availability")
def check_availability(
    test_category: str,
    subject: str,
    subtype: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Check available NEW questions (never seen before)
    """
    try:
        selector = SmartQuestionSelector(db_session=db)
        
        stats = selector.get_available_question_count(
            user_id=current_user.user_id,
            test_category=test_category,
            subject=subject,
            subtype=subtype
        )
        
        return {
            'status': 'success',
            'data': {
                'test_category': stats['test_category'],
                'subject': stats['subject'],
                'total_available': stats['total_available'],
                'by_difficulty': stats['by_difficulty'],
                'can_create_50q_session': stats['can_create_50q_session']
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# ============================================================================
# USER STATS (FIXED - PROPERLY CALCULATE FROM questions_data + user_answers)
# ============================================================================

@router.get("/stats")
def get_user_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user's lifetime statistics
    ✅ HYBRID: Uses user_answers OR correct_count (fallback)
    """
    try:
        print("="*70)
        print("📊 GET USER STATS REQUEST")
        print("="*70)
        print(f"User ID: {current_user.user_id}")
        print(f"Username: {current_user.username}")
        
        # Get all completed sessions
        sessions = db.query(QuestionSession).filter(
            QuestionSession.user_id == current_user.user_id,
            QuestionSession.status.in_(['completed', 'selesai'])
        ).all()
        
        print(f"\n📊 Found {len(sessions)} completed sessions")
        
        # Initialize counters
        total_sessions = len(sessions)
        total_questions = 0
        total_correct = 0
        subject_stats = {}
        difficulty_stats = {
            'mudah': {'total': 0, 'correct': 0, 'accuracy': 0.0},
            'sedang': {'total': 0, 'correct': 0, 'accuracy': 0.0},
            'sulit': {'total': 0, 'correct': 0, 'accuracy': 0.0}
        }
        best_score = 0.0
        
        # Process each session
        for session in sessions:
            print(f"\n📝 Processing session: {session.session_id}")
            print(f"   Subject: {session.subject}")
            print(f"   Status: {session.status}")
            
            # Get questions data and user answers
            questions_data = session.questions_data or []
            user_answers = session.user_answers or {}
            
            print(f"   Questions in data: {len(questions_data)}")
            print(f"   User answers: {len(user_answers)}")
            
            # ✅ HYBRID METHOD: Try user_answers first, fallback to correct_count
            if user_answers and len(user_answers) > 0:
                # METHOD 1: Calculate from user_answers (DETAILED)
                print(f"   📊 Method: Calculate from user_answers (detailed)")
                
                session_correct = 0
                session_total = len(questions_data)
                
                for question in questions_data:
                    question_id = question.get('question_id')
                    correct_answer = question.get('correct_answer')
                    difficulty = question.get('difficulty', 'sedang')
                    subject = question.get('subject', session.subject)
                    
                    if not question_id or not correct_answer:
                        continue
                    
                    # Check if user answered
                    user_answer = user_answers.get(question_id)
                    
                    if user_answer:
                        is_correct = (user_answer == correct_answer)
                        
                        if is_correct:
                            session_correct += 1
                            if difficulty in difficulty_stats:
                                difficulty_stats[difficulty]['correct'] += 1
                        
                        # Count answered
                        if difficulty in difficulty_stats:
                            difficulty_stats[difficulty]['total'] += 1
                        
                        # Update subject stats
                        if subject not in subject_stats:
                            subject_stats[subject] = {'total': 0, 'correct': 0, 'accuracy': 0.0}
                        
                        subject_stats[subject]['total'] += 1
                        if is_correct:
                            subject_stats[subject]['correct'] += 1
                
                total_questions += session_total
                total_correct += session_correct
                
            else:
                # METHOD 2: Use correct_count (FALLBACK)
                print(f"   📊 Method: Use correct_count (fallback)")
                
                session_total = session.total_questions or 0
                session_correct = session.correct_count or 0
                
                print(f"   correct_count: {session_correct}")
                print(f"   total_questions: {session_total}")
                
                total_questions += session_total
                total_correct += session_correct
                
                # Update subject stats (no difficulty breakdown available)
                subject = session.subject or 'unknown'
                if subject not in subject_stats:
                    subject_stats[subject] = {'total': 0, 'correct': 0, 'accuracy': 0.0}
                
                subject_stats[subject]['total'] += session_total
                subject_stats[subject]['correct'] += session_correct
            
            print(f"   ✅ Session result: {session_correct}/{session_total} correct")
            
            # Calculate session score for best_score
            if session_total > 0:
                session_score = (session_correct / session_total) * 100
                best_score = max(best_score, session_score)
        
        # Calculate overall accuracy
        overall_accuracy = (total_correct / total_questions * 100) if total_questions > 0 else 0.0
        
        # Calculate subject accuracies
        for subject in subject_stats:
            subj_total = subject_stats[subject]['total']
            subj_correct = subject_stats[subject]['correct']
            subject_stats[subject]['accuracy'] = (subj_correct / subj_total * 100) if subj_total > 0 else 0.0
        
        # Calculate difficulty accuracies
        for diff in difficulty_stats:
            diff_total = difficulty_stats[diff]['total']
            diff_correct = difficulty_stats[diff]['correct']
            difficulty_stats[diff]['accuracy'] = (diff_correct / diff_total * 100) if diff_total > 0 else 0.0
        
        print("\n" + "="*70)
        print("📊 CALCULATED STATS SUMMARY:")
        print("="*70)
        print(f"Total Sessions: {total_sessions}")
        print(f"Total Questions: {total_questions}")
        print(f"Total Correct: {total_correct}")
        print(f"Overall Accuracy: {overall_accuracy:.2f}%")
        print(f"Best Score: {best_score:.2f}%")
        
        print("\n📚 Subject Stats:")
        for subject, stats in subject_stats.items():
            print(f"  {subject}: {stats['correct']}/{stats['total']} ({stats['accuracy']:.2f}%)")
        
        print("\n🎯 Difficulty Stats:")
        for diff, stats in difficulty_stats.items():
            print(f"  {diff}: {stats['correct']}/{stats['total']} ({stats['accuracy']:.2f}%)")
        
        print("="*70)
        
        return {
            'status': 'success',
            'data': {
                'total_sessions': total_sessions,
                'total_questions': total_questions,
                'total_correct': total_correct,
                'overall_accuracy': round(overall_accuracy, 2),
                'subject_stats': subject_stats,
                'difficulty_stats': difficulty_stats,
                'best_score': round(best_score, 2),
                'questions_seen': total_questions
            }
        }
        
    except Exception as e:
        print(f"\n{'='*70}")
        print("❌ ERROR CALCULATING STATS")
        print("="*70)
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        print("="*70)
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error calculating stats: {str(e)}"
        )

# ============================================================================
# CREATE SESSION (USING SESSION MANAGER)
# ============================================================================

@router.post("/create")
def create_session(
    session_data: SessionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create NEW session with fresh questions (NEVER REPEAT + BACKFILL)
    """
    
    print("="*70)
    print("📥 CREATE SESSION REQUEST")
    print("="*70)
    
    try:
        subject_dist = {}
        single_subject = None
        count = None
        total_questions = 0
        
        # Try NEW format first (subject_distribution)
        if hasattr(session_data, 'subject_distribution') and session_data.subject_distribution:
            print("📦 Format: NEW (subject_distribution)")
            total_questions = sum(session_data.subject_distribution.values())
            subject_dist = session_data.subject_distribution
            
            if len(subject_dist) == 1:
                single_subject = list(subject_dist.keys())[0] if len(subject_dist) == 1 else None
                count = subject_dist[single_subject] if single_subject else total_questions

            else:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Multiple subjects not supported in one session"
                )
        else:
            # OLD format (individual fields)
            print("📦 Format: OLD (subject + question_count)")
            single_subject = getattr(session_data, 'subject', None)
            count = getattr(session_data, 'question_count', 10)
            total_questions = count
            subject_dist = {single_subject: count} if single_subject else {}
        
        # Validate required fields
        if not session_data.test_category:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Missing required field: test_category"
            )
        
        if not single_subject:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Missing required field: subject or subject_distribution"
            )
        
        if not count or count <= 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="question_count must be greater than 0"
            )
        
        print(f"✅ Validated:")
        print(f"   Category: {session_data.test_category}")
        print(f"   Subject: {single_subject}")
        print(f"   Count: {count}")
        print(f"   Total: {total_questions}")
        
        # Enforce tier limits
        enforce_tier_limit(current_user, "create_session", question_count=total_questions)
        
        # Get mode and difficulty
        mode = getattr(session_data, 'mode', 'practice')
        
        # Default difficulty (will be overridden to 'hard' by manager if hardlock is on)
        requested_difficulty = getattr(session_data, 'difficulty', 'sedang')
        
        print(f"   Mode: {mode}")
        print(f"   Requested Difficulty: {requested_difficulty}")
        print("="*70)
        
        # Create session using SessionManager
        manager = SessionManager(db_session=db)
        
        result = manager.create_new_session(
            user_id=current_user.user_id,
            session_type=mode,
            test_category=session_data.test_category,
            subject=single_subject,
            count=count,
            subtype=getattr(session_data, 'subtype', None)
        )
        
        if not isinstance(result, dict):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="SessionManager returned invalid response"
            )

        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("message", "Failed to create session")
            )
        
        # Format response for client
        questions_for_client = []
        for q in result['questions']:
            client_q = {
                'question_id': q['question_id'],
                'test_category': session_data.test_category,
                'subject': q.get('subject', single_subject),
                'subtype': q.get('subtype'),
                'difficulty': q['difficulty'],
                'question_text': q['question_text'],
                'options': q['options'],
                'is_simulation': False
            }
            questions_for_client.append(client_q)
        
        print(f"✅ Session created: {result['session_id']}")
        print(f"   Questions: {result['total_questions']}")
        print("="*70 + "\n")
        
        return {
            'status': 'success',
            'message': f'Session berhasil dibuat dengan {result["total_questions"]} soal BARU',
            'data': {
                'session_id': result['session_id'],
                'test_category': result['test_category'],
                'mode': mode,
                'difficulty': 'hard', 
                'total_questions': result['total_questions'],
                'time_limit_minutes': result['time_limit'],
                'status': 'created',
                'questions': questions_for_client,
                'is_new_questions': True
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error creating session: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating session: {str(e)}"
        )

# ============================================================================
# CREATE REVIEW SESSION
# ============================================================================

@router.post("/create-review")
def create_review_session(
    original_session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create REVIEW session from past session
    """
    try:
        manager = SessionManager(db_session=db)
        
        result = manager.create_review_session(
            user_id=current_user.user_id,
            original_session_id=original_session_id
        )
        
        if not result.get('success'):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result.get('error', 'Session not found')
            )
        
        # Format for client
        questions_for_client = []
        for q in result['questions']:
            client_q = {
                'question_id': q['question_id'],
                'question_text': q['question_text'],
                'options': q['options'],
                'difficulty': q['difficulty']
            }
            
            # Add previous answer if available
            if 'previous_answer' in q:
                client_q['previous_answer'] = q['previous_answer']
            
            questions_for_client.append(client_q)
        
        return {
            'status': 'success',
            'message': f'Review session dibuat dari session sebelumnya',
            'data': {
                'session_id': result['session_id'],
                'original_session_id': original_session_id,
                'is_review_mode': True,
                'total_questions': result['total_questions'],
                'time_limit': result['time_limit'],
                'original_score': result.get('original_score'),
                'original_completed_at': result.get('original_completed_at'),
                'questions': questions_for_client
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# ============================================================================
# LIST SESSIONS
# ============================================================================

@router.get("/")
def list_sessions(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status_filter: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List user's sessions"""
    
    query = db.query(QuestionSession).filter(
        QuestionSession.user_id == current_user.user_id
    )
    
    if status_filter:
        query = query.filter(QuestionSession.status == status_filter)
    
    query = query.order_by(QuestionSession.created_at.desc())
    
    total = query.count()
    sessions = query.offset(skip).limit(limit).all()
    
    sessions_data = []
    for s in sessions:
        session_dict = {
            'session_id': s.session_id,
            'test_category': s.test_category,
            'mode': s.mode,
            'difficulty': s.difficulty,
            'total_questions': s.total_questions,
            'status': s.status,
            'score': s.score,
            'created_at': s.created_at,
            'completed_at': s.completed_at
        }
        
        # Add percentage if we have max_score
        if s.max_score:
            session_dict['percentage'] = round((s.score / s.max_score * 100), 2)
        
        sessions_data.append(session_dict)
    
    return {
        'sessions': sessions_data,
        'total': total,
        'skip': skip,
        'limit': limit
    }

# ============================================================================
# SESSION HISTORY
# ============================================================================

@router.get("/history")
def get_session_history(
    limit: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get session history.
    ✅ FIXED: Included 'created', 'in_progress', 'active' so frontend recovery can find them.
    """
    
    sessions = db.query(QuestionSession).filter(
        QuestionSession.user_id == current_user.user_id,
        # Mengizinkan sesi AKTIF agar bisa diambil oleh Frontend Recovery (session.js)
        QuestionSession.status.in_(['completed', 'selesai', 'created', 'in_progress', 'active'])
    ).order_by(
        QuestionSession.created_at.desc() # Sort by created_at to get newest first
    ).limit(limit).all()
    
    history = []
    for s in sessions:
        session_dict = {
            'session_id': s.session_id,
            'test_category': s.test_category,
            'subject': s.subject,
            'mode': s.mode,
            'difficulty': s.difficulty,
            'total_questions': s.total_questions,
            'score': s.score,
            'max_score': s.max_score,
            'status': s.status,  # Added status to response
            'correct_count': s.correct_count or 0, # FIXED: Handle NULL
            'incorrect_count': s.incorrect_count or 0, # FIXED: Handle NULL
            'completed_at': s.completed_at.isoformat() if s.completed_at else None,
            'created_at': s.created_at.isoformat() if s.created_at else None,
            'can_review': s.can_review if hasattr(s, 'can_review') else True
        }
        
        if s.max_score and s.max_score > 0:
            session_dict['percentage'] = round(((s.score or 0) / s.max_score * 100), 2)
        else:
            session_dict['percentage'] = 0
        
        history.append(session_dict)
    
    return {
        'status': 'success',
        'data': history
    }

# ============================================================================
# GET SESSION DETAILS
# ============================================================================

@router.get("/{session_id}")
def get_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get session details"""
    
    session = db.query(QuestionSession).filter(
        QuestionSession.session_id == session_id,
        QuestionSession.user_id == current_user.user_id
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    # Format questions based on session status
    questions_for_client = []
    
    # Safety check: ensure questions_data is iterable
    q_data_source = session.questions_data if session.questions_data else []

    for q in q_data_source:
        client_q = {
            'question_id': q['question_id'],
            'test_category': q.get('test_category'),
            'subject': q.get('subject'),
            'subtype': q.get('subtype'),
            'difficulty': q['difficulty'],
            'question_text': q['question_text'],
            'options': q['options']
        }
        
        # Show answers only if session completed
        if session.status in ['selesai', 'completed']:
            client_q['correct_answer'] = q.get('correct_answer')
            client_q['answer_scores'] = q.get('answer_scores')
            
            # Show explanation based on tier
            if q.get('explanation'):
                user_tier = current_user.tier
                explanation_tier = q.get('explanation_tier', 'premium')
                
                tier_hierarchy = {'free': 0, 'basic': 1, 'premium': 2, 'admin': 3}
                
                if tier_hierarchy.get(user_tier, 0) >= tier_hierarchy.get(explanation_tier, 2):
                    client_q['explanation'] = q['explanation']
        
        questions_for_client.append(client_q)
    
    return {
        'session_id': session.session_id,
        'test_category': session.test_category,
        'mode': session.mode,
        'difficulty': session.difficulty,
        'subject_distribution': session.subject_distribution,
        'total_questions': session.total_questions,
        'status': session.status,
        'time_limit_minutes': session.time_limit_minutes or session.time_limit,
        'started_at': session.started_at,
        'completed_at': session.completed_at,
        'created_at': session.created_at,
        'user_answers': session.user_answers or {},
        'score': session.score or 0,
        'max_score': session.max_score or 0,
        'results': session.results,
        'questions': questions_for_client # Frontend looks for this property
    }

# ============================================================================
# START SESSION (✅ FIXED: 'active' -> 'in_progress')
# ============================================================================

@router.post("/{session_id}/start")
def start_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Start a session (activate timer)"""
    
    session = db.query(QuestionSession).filter(
        QuestionSession.session_id == session_id,
        QuestionSession.user_id == current_user.user_id
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    # 1. FIX: Cek Idempotency (Jika sudah started, langsung sukses)
    if session.status == 'in_progress':
        return {
            'status': 'success',
            'message': 'Session already started',
            'data': {
                'session_id': session.session_id,
                'started_at': session.started_at,
                'time_limit_minutes': session.time_limit_minutes or session.time_limit
            }
        }

    # 2. FIX: Pastikan statusnya 'created' sebelum di-start
    if session.status != 'created':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session cannot be started (already completed or abandoned)"
        )
    
    # 3. FIX: Ubah ke 'in_progress' (JANGAN 'active')
    session.status = 'in_progress'
    
    if not session.started_at:
        session.started_at = datetime.now(timezone.utc)
    
    db.commit()
    
    return {
        'status': 'success',
        'message': 'Session started',
        'data': {
            'session_id': session.session_id,
            'started_at': session.started_at,
            'time_limit_minutes': session.time_limit_minutes or session.time_limit
        }
    }

# ============================================================================
# SUBMIT SINGLE ANSWER (✅ ADDED MISSING ENDPOINT)
# ============================================================================

@router.post("/{session_id}/answer")
def submit_answer(
    session_id: str,
    answer_data: SubmitAnswerRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Submit single answer during session"""
    try:
        manager = SessionManager(db_session=db)
        
        result = manager.submit_answer(
            session_id=session_id,
            question_id=answer_data.question_id,
            user_answer=answer_data.user_answer,
            time_spent=answer_data.time_spent
        )
        
        return {
            'status': 'success',
            'data': result
        }
        
    except Exception as e:
        print(f"❌ Error submitting answer: {str(e)}") # Log error for debugging
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# ============================================================================
# COMPLETE SESSION
# ============================================================================

@router.post("/{session_id}/submit")
def submit_session(
    session_id: str,
    submission: SessionSubmit,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Submit all answers and complete session"""
    
    session = db.query(QuestionSession).filter(
        QuestionSession.session_id == session_id,
        QuestionSession.user_id == current_user.user_id
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    if session.status in ['selesai', 'completed']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session already completed"
        )
    
    try:
        manager = SessionManager(db_session=db)
        result = manager.complete_session(session_id=session_id)
        
        if not result.get('success'):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to complete session"
            )
        
        detailed_results = calculate_score(submission.answers, session.questions_data)
        update_user_progress(db, current_user.user_id, detailed_results)
        
        return {
            'status': 'success',
            'message': 'Session completed',
            'data': {
                'session_id': session.session_id,
                'score': result['score'],
                'correct': result['correct_count'],
                'incorrect': result['incorrect_count'],
                'unanswered': result['unanswered_count'],
                'total': result['total_questions'],
                'percentage': result['score'],
                'by_subject': detailed_results.get('by_subject', {})
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# ============================================================================
# DELETE SESSION
# ============================================================================

@router.delete("/{session_id}")
def delete_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a session"""
    
    session = db.query(QuestionSession).filter(
        QuestionSession.session_id == session_id,
        QuestionSession.user_id == current_user.user_id
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    db.delete(session)
    db.commit()
    
    return {
        'status': 'success',
        'message': 'Session deleted',
        'data': None
    }

# ============================================================================
# REVIEW ENDPOINTS (NEW - FIX FOR EMPTY REVIEW TAB)
# ============================================================================

@router.get("/review/list")
def get_reviewable_sessions(
    limit: int = Query(20, ge=1, le=100),
    subject: Optional[str] = None,
    score_filter: Optional[str] = None, # 'high', 'low', 'medium'
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get sessions available for review (Completed sessions)
    """
    query = db.query(QuestionSession).filter(
        QuestionSession.user_id == current_user.user_id,
        QuestionSession.status.in_(['completed', 'selesai']),
        QuestionSession.can_review == True
    )

    # Filter by subject
    if subject and subject != 'all':
        query = query.filter(QuestionSession.subject == subject)

    # Sort logic based on filter
    if score_filter == 'low':
        query = query.order_by(QuestionSession.score.asc())
    elif score_filter == 'high':
        query = query.order_by(QuestionSession.score.desc())
    else:
        # Default: Most recent first
        query = query.order_by(QuestionSession.created_at.desc())

    sessions = query.limit(limit).all()

    data = []
    for s in sessions:
        # FIXED: Handle NULL values
        percentage = ((s.score or 0) / s.max_score * 100) if s.max_score else 0
        data.append({
            'session_id': s.session_id,
            'test_category': s.test_category,
            'subject': s.subject,
            'total_questions': s.total_questions,
            'score': s.score or 0,
            'max_score': s.max_score or 0,
            'percentage': round(percentage, 1),
            'correct_count': s.correct_count or 0,
            'created_at': s.created_at.isoformat() if s.created_at else None
        })

    return {
        'status': 'success',
        'data': data
    }

@router.get("/review/stats")
def get_review_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get statistics specifically for Review Page
    """
    # 1. Total Completed Sessions
    # FIXED: Support both status types
    total_sessions = db.query(QuestionSession).filter(
        QuestionSession.user_id == current_user.user_id,
        QuestionSession.status.in_(['completed', 'selesai'])
    ).count()

    # 2. Average Score
    # FIXED: Support both status types
    avg_score_query = db.query(func.avg(QuestionSession.score)).filter(
        QuestionSession.user_id == current_user.user_id,
        QuestionSession.status.in_(['completed', 'selesai'])
    ).scalar()
    avg_score = round(avg_score_query, 1) if avg_score_query else 0

    # 3. Best Score
    # FIXED: Support both status types
    best_score = db.query(func.max(QuestionSession.score)).filter(
        QuestionSession.user_id == current_user.user_id,
        QuestionSession.status.in_(['completed', 'selesai'])
    ).scalar() or 0

    # 4. Most Recent Session
    # FIXED: Support both status types
    recent = db.query(QuestionSession).filter(
        QuestionSession.user_id == current_user.user_id,
        QuestionSession.status.in_(['completed', 'selesai'])
    ).order_by(QuestionSession.created_at.desc()).first()

    recent_data = None
    if recent:
        # FIXED: Handle NULL values
        recent_data = {
            'subject': recent.subject,
            'score': recent.score or 0,
            'max_score': recent.max_score or 0,
            'percentage': round(((recent.score or 0) / recent.max_score * 100), 1) if recent.max_score else 0
        }

    return {
        'status': 'success',
        'data': {
            'total_sessions_completed': total_sessions,
            'total_reviewable': total_sessions, # Same for now
            'avg_score': avg_score,
            'best_score': best_score,
            'most_recent_session': recent_data
        }
    }