"""
Exam Mode Router
PREMIUM ONLY feature - Mixed subject exams
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import get_db
from models import User, Question, QuestionSession, QuestionUsage
from core.dependencies import require_premium, validate_test_access
from pydantic import BaseModel
import uuid
import random
from datetime import datetime, timezone

router = APIRouter(prefix="/exam", tags=["Exam Mode"])

# ============================================================================
# SCHEMAS
# ============================================================================

class ExamSessionCreate(BaseModel):
    """Create exam mode session"""
    test_category: str  # 'cpns' or 'polri'
    
    class Config:
        json_schema_extra = {
            "example": {
                "test_category": "cpns"
            }
        }

# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/create")
def create_exam_session(
    exam_data: ExamSessionCreate,
    current_user: User = Depends(require_premium),  # PREMIUM ONLY
    db: Session = Depends(get_db)
):
    """
    Create EXAM MODE session (PREMIUM only)
    
    CPNS Exam: 50 TIU + 50 TWK + 50 TKP = 150 questions (120 minutes)
    POLRI Exam: 50 Bahasa Inggris + 50 TIU + 50 TWK = 150 questions (120 minutes)
    
    Features:
    - Mixed subjects in one session
    - Realistic exam simulation
    - Time limit enforced
    - Never repeat questions
    """
    
    try:
        test_category = exam_data.test_category.lower()
        
        # Validate access
        validate_test_access(current_user, test_category)
        
        # Define exam structure
        if test_category == 'cpns':
            subject_distribution = {
                'tiu': 50,
                'twk': 50,
                'tkp': 50
            }
            time_limit = 120  # 2 hours
        elif test_category == 'polri':
            subject_distribution = {
                'bahasa_inggris': 50,
                'tiu': 50,
                'twk': 50
            }
            time_limit = 120  # 2 hours
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid test category: {test_category}. Must be 'cpns' or 'polri'"
            )
        
        # Create session
        session_id = str(uuid.uuid4())
        total_questions = sum(subject_distribution.values())
        
        # Get questions for each subject
        all_questions = []
        
        for subject, count in subject_distribution.items():
            # Get IDs of questions already seen by this user for this subject
            seen_query = db.query(QuestionUsage.question_id).filter(
                QuestionUsage.user_id == current_user.user_id,
            ).join(Question).filter(
                Question.subject == subject
            )
            seen_ids = [row[0] for row in seen_query.all()]
            
            # Query for unseen questions
            query = db.query(Question).filter(
                Question.test_category == test_category,
                Question.subject == subject
            )
            
            if seen_ids:
                query = query.filter(Question.question_id.notin_(seen_ids))
            
            # Get questions with balanced difficulty
            easy_count = count // 3
            medium_count = count // 3
            hard_count = count - easy_count - medium_count
            
            questions = []
            
            # Get easy questions
            easy_qs = query.filter(Question.difficulty == 'mudah').order_by(func.random()).limit(easy_count).all()
            questions.extend(easy_qs)
            
            # Get medium questions
            medium_qs = query.filter(Question.difficulty == 'sedang').order_by(func.random()).limit(medium_count).all()
            questions.extend(medium_qs)
            
            # Get hard questions
            hard_qs = query.filter(Question.difficulty == 'sulit').order_by(func.random()).limit(hard_count).all()
            questions.extend(hard_qs)
            
            # Check if we have enough questions
            if len(questions) < count:
                available = len(questions)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error": "insufficient_questions",
                        "message": f"Not enough unseen questions for {subject}",
                        "subject": subject,
                        "required": count,
                        "available": available
                    }
                )
            
            all_questions.extend(questions)
        
        # Shuffle all questions
        random.shuffle(all_questions)
        
        # Create session
        questions_data = [
            {
                'question_id': q.question_id,
                'question_text': q.question_text,
                'options': q.options,
                'difficulty': q.difficulty,
                'subject': q.subject,
                'correct_answer': q.correct_answer
            }
            for q in all_questions
        ]
        
        new_session = QuestionSession(
            session_id=session_id,
            user_id=current_user.user_id,
            test_category=test_category,
            mode='exam',  # EXAM MODE
            session_type='exam',
            difficulty='mixed',
            total_questions=total_questions,
            questions_data=questions_data,
            subject_distribution=subject_distribution,
            time_limit_minutes=time_limit,
            status='created',
            created_at=datetime.now(timezone.utc)
        )
        
        db.add(new_session)
        
        # Mark questions as used
        for question in all_questions:
            usage = QuestionUsage(
                question_id=question.question_id,
                user_id=current_user.user_id,
                session_id=session_id,
                used_at=datetime.now(timezone.utc)
            )
            db.add(usage)
            
            # Update question usage stats
            question.usage_count += 1
            question.is_used = True
            question.last_used_at = datetime.now(timezone.utc)
        
        db.commit()
        db.refresh(new_session)
        
        # Prepare response (hide correct answers)
        response_questions = [
            {
                'question_id': q['question_id'],
                'question_text': q['question_text'],
                'options': q['options'],
                'difficulty': q['difficulty'],
                'subject': q['subject']
                # correct_answer is hidden until answered
            }
            for q in questions_data
        ]
        
        return {
            'status': 'success',
            'message': f'Exam session created with {total_questions} questions',
            'data': {
                'session_id': session_id,
                'test_category': test_category,
                'mode': 'exam',
                'session_type': 'exam',
                'total_questions': total_questions,
                'time_limit_minutes': time_limit,
                'subject_distribution': subject_distribution,
                'questions': response_questions
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"❌ Error creating exam session: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create exam session: {str(e)}"
        )

@router.get("/availability/{test_category}")
def check_exam_availability(
    test_category: str,
    current_user: User = Depends(require_premium),
    db: Session = Depends(get_db)
):
    """
    Check if user has enough unseen questions for exam mode
    """
    
    try:
        test_category = test_category.lower()
        
        # Validate access
        validate_test_access(current_user, test_category)
        
        # Define required questions
        if test_category == 'cpns':
            required = {'tiu': 50, 'twk': 50, 'tkp': 50}
        elif test_category == 'polri':
            required = {'bahasa_inggris': 50, 'tiu': 50, 'twk': 50}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid test category: {test_category}"
            )
        
        availability = {}
        can_create_exam = True
        
        for subject, count in required.items():
            # Get seen question IDs
            seen_query = db.query(QuestionUsage.question_id).filter(
                QuestionUsage.user_id == current_user.user_id
            ).join(Question).filter(
                Question.subject == subject
            )
            seen_ids = [row[0] for row in seen_query.all()]
            
            # Count available questions
            query = db.query(func.count(Question.question_id)).filter(
                Question.test_category == test_category,
                Question.subject == subject
            )
            
            if seen_ids:
                query = query.filter(Question.question_id.notin_(seen_ids))
            
            available = query.scalar()
            
            availability[subject] = {
                'required': count,
                'available': available,
                'sufficient': available >= count
            }
            
            if available < count:
                can_create_exam = False
        
        return {
            'status': 'success',
            'data': {
                'test_category': test_category,
                'can_create_exam': can_create_exam,
                'total_required': sum(required.values()),
                'subjects': availability
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error checking exam availability: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )