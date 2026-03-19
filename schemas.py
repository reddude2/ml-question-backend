"""
Pydantic Schemas
Request and response models
✅ FIXED: SessionCreate now accepts both old & new formats
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict
from datetime import datetime

# ============================================================================
# AUTH SCHEMAS
# ============================================================================

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    status: str
    message: str
    access_token: str
    token_type: str
    user: dict

class PasswordChange(BaseModel):
    old_password: str
    new_password: str

# ============================================================================
# USER SCHEMAS
# ============================================================================

class UserResponse(BaseModel):
    user_id: str
    username: str
    full_name: str
    role: str
    test_type: str
    tier: str
    is_active: bool
    subscription_start: Optional[datetime]
    subscription_end: Optional[datetime]
    days_remaining: Optional[int]
    is_expired: Optional[bool] = False

class UserCreate(BaseModel):
    username: str
    password: Optional[str] = None
    full_name: str
    role: str = "user"
    test_type: str
    tier: str = "free"
    subscription_days: int = 30

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    test_type: Optional[str] = None
    tier: Optional[str] = None
    is_active: Optional[bool] = None
    subscription_days: Optional[int] = None

class UserList(BaseModel):
    users: List[dict]
    total: int
    skip: int
    limit: int

# ============================================================================
# QUESTION SCHEMAS
# ============================================================================

class QuestionResponse(BaseModel):
    question_id: str
    test_category: str
    subject: str
    subtype: Optional[str]
    difficulty: str
    question_text: str
    options: dict
    correct_answer: Optional[str]
    answer_scores: Optional[dict]
    explanation: Optional[str]
    explanation_tier: Optional[str]
    is_simulation: bool
    quality_score: float
    usage_count: int
    correct_rate: float

class QuestionCreate(BaseModel):
    test_category: str
    subject: str
    subtype: Optional[str] = None
    difficulty: str
    question_text: str
    options: dict
    correct_answer: Optional[str] = None
    answer_scores: Optional[dict] = None
    explanation: Optional[str] = None
    explanation_tier: str = "basic"
    is_simulation: bool = False

class QuestionUpdate(BaseModel):
    test_category: Optional[str] = None
    subject: Optional[str] = None
    subtype: Optional[str] = None
    difficulty: Optional[str] = None
    question_text: Optional[str] = None
    options: Optional[dict] = None
    correct_answer: Optional[str] = None
    answer_scores: Optional[dict] = None
    explanation: Optional[str] = None
    explanation_tier: Optional[str] = None
    is_simulation: Optional[bool] = None
    quality_score: Optional[float] = None

class QuestionList(BaseModel):
    questions: List[dict]
    total: int
    skip: int
    limit: int

class RandomQuestionsRequest(BaseModel):
    test_category: str
    count: int
    difficulty: Optional[str] = None
    subject_distribution: Optional[Dict[str, int]] = None

# ============================================================================
# SESSION SCHEMAS - ✅ FIXED FOR BOTH OLD & NEW FORMATS
# ============================================================================

class SessionCreate(BaseModel):
    """
    Flexible session creation - accepts BOTH formats:
    
    OLD FORMAT (desktop app):
    {
        "test_category": "polri",
        "subject": "bahasa_inggris",
        "difficulty": "sedang",
        "question_count": 10
    }
    
    NEW FORMAT (web app):
    {
        "test_category": "polri",
        "subject_distribution": {"bahasa_inggris": 10},
        "mode": "practice",
        "difficulty": "sedang"
    }
    """
    
    # ✅ Required field
    test_category: str = Field(..., description="Test category (cpns/polri)")
    
    # ✅ OLD FORMAT fields (desktop app)
    subject: Optional[str] = Field(None, description="Single subject for session")
    question_count: Optional[int] = Field(10, ge=1, le=200, description="Number of questions")
    
    # ✅ NEW FORMAT fields (web app)
    subject_distribution: Optional[Dict[str, int]] = Field(None, description="Multi-subject distribution")
    
    # ✅ Common fields
    mode: Optional[str] = Field('practice', description="Session mode (practice/exam)")
    difficulty: Optional[str] = Field('sedang', description="Difficulty level (mudah/sedang/sulit)")
    time_limit_minutes: Optional[int] = Field(None, description="Time limit in minutes")
    
    # ✅ Optional fields
    subtype: Optional[str] = Field(None, description="Subject subtype if applicable")
    is_exam_mode: Optional[bool] = Field(False, description="Is this an exam session")
    session_type: Optional[str] = Field('standard', description="Session type")
    
    class Config:
        extra = 'allow'  # ✅ Allow extra fields without error
        schema_extra = {
            "examples": [
                {
                    "description": "OLD FORMAT (Desktop App)",
                    "value": {
                        "test_category": "polri",
                        "subject": "bahasa_inggris",
                        "difficulty": "sedang",
                        "question_count": 10
                    }
                },
                {
                    "description": "NEW FORMAT (Web App)",
                    "value": {
                        "test_category": "polri",
                        "subject_distribution": {"bahasa_inggris": 10},
                        "mode": "practice",
                        "difficulty": "sedang"
                    }
                }
            ]
        }
    
    @validator('subject_distribution', always=True)
    def validate_has_subject_info(cls, v, values):
        """Ensure we have either subject or subject_distribution"""
        subject = values.get('subject')
        if not v and not subject:
            raise ValueError('Must provide either subject or subject_distribution')
        return v
    
    @validator('difficulty')
    def validate_difficulty(cls, v):
        """Ensure difficulty is valid"""
        if v and v not in ['mudah', 'sedang', 'sulit']:
            raise ValueError('Difficulty must be one of: mudah, sedang, sulit')
        return v
    
    @validator('mode')
    def validate_mode(cls, v):
        """Ensure mode is valid"""
        if v and v not in ['practice', 'exam']:
            raise ValueError('Mode must be either: practice or exam')
        return v

class SessionResponse(BaseModel):
    session_id: str
    user_id: str
    test_category: str
    mode: str
    difficulty: str
    subject_distribution: dict
    total_questions: int
    questions: list
    status: str
    time_limit_minutes: Optional[int]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    user_answers: dict
    score: Optional[float]
    max_score: Optional[float]
    results: Optional[dict]

class SessionList(BaseModel):
    sessions: List[dict]
    total: int
    skip: int
    limit: int

class SessionSubmit(BaseModel):
    answers: Dict[str, str]

class SessionResults(BaseModel):
    session_id: str
    status: str
    total_questions: int
    answered: int
    correct: int
    score: float
    max_score: float
    percentage: float
    by_subject: dict
    questions_with_answers: list
    user_answers: dict
    completed_at: datetime

# ============================================================================
# PROGRESS SCHEMAS
# ============================================================================

class ProgressResponse(BaseModel):
    user_id: str
    total_sessions: int
    total_questions: int
    total_correct: int
    overall_accuracy: float
    subject_stats: dict
    last_activity: Optional[datetime]
    updated_at: Optional[datetime]

class ProgressSummary(BaseModel):
    period_days: int
    start_date: datetime
    end_date: datetime
    total_sessions: int
    completed_sessions: int
    total_questions: int
    average_score: float
    subject_breakdown: dict

# ============================================================================
# ADMIN SCHEMAS
# ============================================================================

class DashboardStats(BaseModel):
    users: dict
    questions: dict
    sessions: dict
    generated_at: datetime

class AuditLogList(BaseModel):
    logs: List[dict]
    total: int
    skip: int
    limit: int

# ============================================================================
# GENERIC SCHEMAS
# ============================================================================

class SuccessResponse(BaseModel):
    status: str
    message: str
    data: Optional[dict] = None