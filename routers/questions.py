"""
Questions Router
Question bank management and random selection
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import get_db
from models import User, Question
from schemas import (
    QuestionResponse, QuestionCreate, QuestionUpdate, 
    QuestionList, RandomQuestionsRequest
)
from core.dependencies import get_current_user, admin_required
from core.access_control import (
    validate_test_category_access,
    validate_subject_access,
    get_allowed_test_categories,
    get_allowed_subjects
)
from typing import Optional, List
import random

router = APIRouter(prefix="/questions", tags=["Questions"])

# ============================================================================
# LIST QUESTIONS
# ============================================================================

@router.get("/", response_model=QuestionList)
def list_questions(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    test_category: Optional[str] = None,
    subject: Optional[str] = None,
    difficulty: Optional[str] = None,
    is_simulation: Optional[bool] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List questions with filters
    
    User can only see questions from allowed test categories
    """
    
    query = db.query(Question)
    
    # Filter by user's allowed test categories
    allowed_categories = get_allowed_test_categories(current_user.test_type)
    
    if test_category:
        if test_category not in allowed_categories:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied to {test_category} questions"
            )
        query = query.filter(Question.test_category == test_category)
    else:
        query = query.filter(Question.test_category.in_(allowed_categories))
    
    # Other filters
    if subject:
        validate_subject_access(current_user.test_type, subject)
        query = query.filter(Question.subject == subject)
    
    if difficulty:
        query = query.filter(Question.difficulty == difficulty)
    
    if is_simulation is not None:
        query = query.filter(Question.is_simulation == is_simulation)
    
    if search:
        query = query.filter(Question.question_text.ilike(f"%{search}%"))
    
    total = query.count()
    questions = query.offset(skip).limit(limit).all()
    
    # Format questions
    questions_data = []
    for q in questions:
        q_data = {
            "question_id": q.question_id,
            "test_category": q.test_category,
            "subject": q.subject,
            "subtype": q.subtype,
            "difficulty": q.difficulty,
            "question_text": q.question_text,
            "options": q.options,
            "correct_answer": q.correct_answer,
            "answer_scores": q.answer_scores,
            "explanation": q.explanation,
            "explanation_tier": q.explanation_tier,
            "is_simulation": q.is_simulation,
            "quality_score": q.quality_score,
            "usage_count": q.usage_count,
            "correct_rate": q.correct_rate
        }
        questions_data.append(q_data)
    
    return {
        "questions": questions_data,
        "total": total,
        "skip": skip,
        "limit": limit
    }

# ============================================================================
# GET QUESTION BY ID
# ============================================================================

@router.get("/{question_id}", response_model=QuestionResponse)
def get_question(
    question_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get question by ID"""
    
    question = db.query(Question).filter(Question.question_id == question_id).first()
    
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found"
        )
    
    # Check access
    validate_test_category_access(current_user.test_type, question.test_category)
    
    return {
        "question_id": question.question_id,
        "test_category": question.test_category,
        "subject": question.subject,
        "subtype": question.subtype,
        "difficulty": question.difficulty,
        "question_text": question.question_text,
        "options": question.options,
        "correct_answer": question.correct_answer,
        "answer_scores": question.answer_scores,
        "explanation": question.explanation,
        "explanation_tier": question.explanation_tier,
        "is_simulation": question.is_simulation,
        "quality_score": question.quality_score,
        "usage_count": question.usage_count,
        "correct_rate": question.correct_rate
    }

# ============================================================================
# CREATE QUESTION (Admin only)
# ============================================================================

@router.post("/", status_code=status.HTTP_201_CREATED)
def create_question(
    question_data: QuestionCreate,
    current_user: User = Depends(admin_required),
    db: Session = Depends(get_db)
):
    """Create new question (Admin only)"""
    
    # Validate data
    if not question_data.correct_answer and not question_data.answer_scores:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must provide either correct_answer or answer_scores"
        )
    
    # Create question
    new_question = Question(
        test_category=question_data.test_category,
        subject=question_data.subject,
        subtype=question_data.subtype,
        difficulty=question_data.difficulty,
        question_text=question_data.question_text,
        options=question_data.options,
        correct_answer=question_data.correct_answer,
        answer_scores=question_data.answer_scores,
        explanation=question_data.explanation,
        explanation_tier=question_data.explanation_tier,
        is_simulation=question_data.is_simulation,
        quality_score=1.0,
        usage_count=0,
        correct_rate=0.0
    )
    
    db.add(new_question)
    db.commit()
    db.refresh(new_question)
    
    return {
        "status": "success",
        "message": "Question created successfully",
        "data": {
            "question_id": new_question.question_id
        }
    }

# ============================================================================
# UPDATE QUESTION (Admin only)
# ============================================================================

@router.put("/{question_id}")
def update_question(
    question_id: str,
    question_data: QuestionUpdate,
    current_user: User = Depends(admin_required),
    db: Session = Depends(get_db)
):
    """Update question (Admin only)"""
    
    question = db.query(Question).filter(Question.question_id == question_id).first()
    
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found"
        )
    
    # Update fields
    if question_data.test_category is not None:
        question.test_category = question_data.test_category
    
    if question_data.subject is not None:
        question.subject = question_data.subject
    
    if question_data.subtype is not None:
        question.subtype = question_data.subtype
    
    if question_data.difficulty is not None:
        question.difficulty = question_data.difficulty
    
    if question_data.question_text is not None:
        question.question_text = question_data.question_text
    
    if question_data.options is not None:
        question.options = question_data.options
    
    if question_data.correct_answer is not None:
        question.correct_answer = question_data.correct_answer
    
    if question_data.answer_scores is not None:
        question.answer_scores = question_data.answer_scores
    
    if question_data.explanation is not None:
        question.explanation = question_data.explanation
    
    if question_data.explanation_tier is not None:
        question.explanation_tier = question_data.explanation_tier
    
    if question_data.is_simulation is not None:
        question.is_simulation = question_data.is_simulation
    
    if question_data.quality_score is not None:
        question.quality_score = question_data.quality_score
    
    db.commit()
    
    return {
        "status": "success",
        "message": "Question updated successfully",
        "data": {"question_id": question.question_id}
    }

# ============================================================================
# DELETE QUESTION (Admin only)
# ============================================================================

@router.delete("/{question_id}")
def delete_question(
    question_id: str,
    current_user: User = Depends(admin_required),
    db: Session = Depends(get_db)
):
    """Delete question (Admin only)"""
    
    question = db.query(Question).filter(Question.question_id == question_id).first()
    
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found"
        )
    
    db.delete(question)
    db.commit()
    
    return {
        "status": "success",
        "message": "Question deleted successfully",
        "data": None
    }

# ============================================================================
# RANDOM QUESTIONS SELECTION
# ============================================================================

@router.post("/random")
def get_random_questions(
    request: RandomQuestionsRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get random questions for practice/exam
    
    Supports subject distribution for balanced selection
    """
    
    # Validate access
    validate_test_category_access(current_user.test_type, request.test_category)
    
    selected_questions = []
    
    if request.subject_distribution:
        # Get questions by subject distribution
        for subject, count in request.subject_distribution.items():
            validate_subject_access(current_user.test_type, subject, request.test_category)
            
            query = db.query(Question).filter(
                Question.test_category == request.test_category,
                Question.subject == subject
            )
            
            if request.difficulty:
                query = query.filter(Question.difficulty == request.difficulty)
            
            # Get random questions for this subject
            available = query.all()
            
            if len(available) < count:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Not enough questions for subject '{subject}'. Need {count}, found {len(available)}"
                )
            
            selected = random.sample(available, count)
            selected_questions.extend(selected)
    
    else:
        # Get random questions from all allowed subjects
        query = db.query(Question).filter(
            Question.test_category == request.test_category
        )
        
        if request.difficulty:
            query = query.filter(Question.difficulty == request.difficulty)
        
        available = query.all()
        
        if len(available) < request.count:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Not enough questions. Need {request.count}, found {len(available)}"
            )
        
        selected_questions = random.sample(available, request.count)
    
    # Format questions (hide correct answers for now)
    questions_data = []
    for q in selected_questions:
        q_data = {
            "question_id": q.question_id,
            "test_category": q.test_category,
            "subject": q.subject,
            "subtype": q.subtype,
            "difficulty": q.difficulty,
            "question_text": q.question_text,
            "options": q.options,
            # Don't send correct_answer/answer_scores yet
            "is_simulation": q.is_simulation
        }
        questions_data.append(q_data)
    
    # Shuffle questions
    random.shuffle(questions_data)
    
    return {
        "status": "success",
        "count": len(questions_data),
        "questions": questions_data
    }