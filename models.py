"""
Database Models
SQLAlchemy ORM models for all tables
UPDATED: Admin Tier, Exam Mode, Branch Access, 4-Tier System, Materials Management, Reading Passages
"""

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, Text,
    DateTime, ForeignKey, CheckConstraint, Index, JSON
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from database import Base
from datetime import datetime, timezone
import uuid
import hashlib

# ============================================================================
# USER MODEL - UPDATED WITH 4 TIERS + BRANCH ACCESS
# ============================================================================

class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "role IN ('admin', 'user_cpns', 'user_polri', 'user_mixed')", 
            name="check_role"
        ),
        CheckConstraint(
            "test_type IN ('cpns', 'polri', 'mixed')", 
            name="check_test_type"
        ),
        CheckConstraint(
            "tier IN ('free', 'basic', 'premium', 'admin')", 
            name="check_tier"
        ),
        CheckConstraint(
            "branch_access IN ('cpns', 'polri', 'both')",
            name="check_branch_access"
        ),
    )
    
    user_id = Column(String(50), primary_key=True, default=lambda: f"user_{uuid.uuid4().hex[:12]}")
    username = Column(String(50), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=False)
    
    role = Column(String(20), default='user_cpns', nullable=False)
    test_type = Column(String(20), default='cpns', nullable=False)
    tier = Column(String(20), default='free', nullable=False)
    branch_access = Column(String(10), default='cpns', nullable=False)
    session_count = Column(Integer, default=0, nullable=False)
    
    is_active = Column(Boolean, default=True, nullable=False)
    
    subscription_start = Column(DateTime(timezone=True), nullable=True)
    subscription_end = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    sessions = relationship("QuestionSession", back_populates="user", cascade="all, delete-orphan")
    progress = relationship("UserProgress", back_populates="user", uselist=False, cascade="all, delete-orphan")
    question_usage = relationship("QuestionUsage", back_populates="user", cascade="all, delete-orphan")

# ============================================================================
# MATERIAL MODEL - UPDATED FOR ML QUESTION GENERATION
# ============================================================================

class Material(Base):
    """
    Store learning materials for ML question generation
    Materials are used to generate questions with Gemini AI
    """
    __tablename__ = "materials"
    __table_args__ = (
        CheckConstraint("test_category IN ('cpns', 'polri')", name="check_material_category"),
        CheckConstraint("difficulty IN ('mudah', 'sedang', 'sulit')", name="check_material_difficulty"),
        Index('idx_materials_category_subject', 'test_category', 'subject'),
        Index('idx_materials_active', 'is_active'),
    )
    
    material_id = Column(String(50), primary_key=True, default=lambda: f"mat_{uuid.uuid4().hex[:12]}")
    
    test_category = Column(String(20), nullable=False, index=True)
    subject = Column(String(50), nullable=False, index=True)
    topic = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    difficulty = Column(String(20), default='sedang', nullable=False)
    
    tags = Column(ARRAY(String), default=list, nullable=True)
    examples = Column(ARRAY(Text), nullable=True)
    extra_data = Column(JSONB, nullable=True)
    
    is_active = Column(Boolean, default=True, nullable=False)
    question_count = Column(Integer, default=0, nullable=False)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    
    questions = relationship("Question", back_populates="material", cascade="all, delete-orphan")

# ============================================================================
# QUESTION MODEL - WITH READING PASSAGE SUPPORT
# ============================================================================

class Question(Base):
    __tablename__ = "questions"
    __table_args__ = (
        CheckConstraint("test_category IN ('polri', 'cpns')", name="check_test_category"),
        CheckConstraint("difficulty IN ('mudah', 'sedang', 'sulit')", name="check_difficulty"),
        CheckConstraint("explanation_tier IN ('free', 'basic', 'premium')", name="check_explanation_tier"),
        Index('idx_questions_material', 'source_material_id'),
        Index('idx_questions_usage', 'is_used', 'usage_count'),
        Index('idx_questions_last_used', 'last_used_at'),
        Index('idx_questions_category_subject', 'test_category', 'subject'),
        Index('idx_questions_active', 'is_active'), # Index added for performance
    )
    
    question_id = Column(String(50), primary_key=True, default=lambda: f"q_{uuid.uuid4().hex[:12]}")
    
    # ML Features
    source_material_id = Column(String(50), ForeignKey('materials.material_id', ondelete='SET NULL'), nullable=True)
    content_hash = Column(String(64), unique=True, nullable=True, index=True)
    
    # Question details
    test_category = Column(String(20), nullable=False, index=True)
    subject = Column(String(50), nullable=False, index=True)
    subtype = Column(String(50), nullable=True)
    difficulty = Column(String(20), nullable=False, index=True)
    
    # ✅ NEW: Reading passage for comprehension questions
    reading_passage = Column(Text, nullable=True)
    
    question_text = Column(Text, nullable=False)
    
    # Options
    option_a = Column(Text, nullable=True)
    option_b = Column(Text, nullable=True)
    option_c = Column(Text, nullable=True)
    option_d = Column(Text, nullable=True)
    option_e = Column(Text, nullable=True)
    options = Column(JSONB, nullable=True)
    
    correct_answer = Column(String(10), nullable=True)
    answer_scores = Column(JSONB, nullable=True)
    
    tags = Column(ARRAY(String), default=list, nullable=True)
    
    # Explanation with tier control
    explanation = Column(Text, nullable=True)
    explanation_tier = Column(String(20), default='basic')
    
    # Quality & statistics
    is_simulation = Column(Boolean, default=False)
    quality_score = Column(Float, default=1.0)
    usage_count = Column(Integer, default=0)
    correct_rate = Column(Float, default=0.0)
    
    # ✅ FIX: Added is_active column here!
    is_active = Column(Boolean, default=True, nullable=False)

    # Usage tracking
    is_used = Column(Boolean, default=False, index=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True, index=True)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Relationships
    material = relationship("Material", back_populates="questions")
    usage_history = relationship("QuestionUsage", back_populates="question", cascade="all, delete-orphan")
    
    def generate_hash(self):
        """Generate content hash for duplicate detection"""
        content = f"{self.question_text}|{self.correct_answer or ''}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.content_hash and self.question_text:
            self.content_hash = self.generate_hash()
        
        if not self.options and self.option_a:
            self.options = {
                'A': self.option_a,
                'B': self.option_b,
                'C': self.option_c,
                'D': self.option_d,
                'E': self.option_e
            }

# ============================================================================
# QUESTION USAGE TRACKING
# ============================================================================

class QuestionUsage(Base):
    """
    Track which user used which question in which session
    Prevents showing same question to same user repeatedly
    """
    __tablename__ = "question_usage"
    __table_args__ = (
        Index('idx_user_question_recent', 'user_id', 'question_id', 'used_at'),
        Index('idx_session_questions', 'session_id', 'question_id'),
    )
    
    usage_id = Column(String(50), primary_key=True, default=lambda: f"use_{uuid.uuid4().hex[:12]}")
    question_id = Column(String(50), ForeignKey('questions.question_id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = Column(String(50), ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False, index=True)
    session_id = Column(String(50), ForeignKey('question_sessions.session_id', ondelete='CASCADE'), nullable=False, index=True)
    
    used_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    
    user_answered = Column(Boolean, default=False, nullable=False)
    user_answer = Column(String(10), nullable=True)
    was_correct = Column(Boolean, nullable=True)
    time_spent = Column(Integer, nullable=True)
    
    question = relationship("Question", back_populates="usage_history")
    user = relationship("User", back_populates="question_usage")
    session = relationship("QuestionSession")

# ============================================================================
# QUESTION SESSION MODEL
# ============================================================================

class QuestionSession(Base):
    __tablename__ = "question_sessions"
    __table_args__ = (
        CheckConstraint("status IN ('created', 'in_progress', 'completed', 'abandoned')", name="check_status"),
        CheckConstraint("mode IN ('practice', 'review', 'exam')", name="check_mode"),
        CheckConstraint("session_type IN ('standard', 'exam')", name="check_session_type"),
        Index('ix_question_sessions_status', 'status'),
        Index('ix_question_sessions_user_mode', 'user_id', 'mode'),
    )
    
    session_id = Column(String(50), primary_key=True)
    user_id = Column(String(50), ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
    
    test_category = Column(String(20), nullable=False)
    difficulty = Column(String(20), nullable=False)
    total_questions = Column(Integer, nullable=False)
    questions_data = Column(JSONB, nullable=False)
    status = Column(String(20), nullable=False, default='created')
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    
    mode = Column(String(20), default='practice', nullable=False)
    
    subject = Column(String(50), nullable=True)
    subtype = Column(String(50), nullable=True)
    
    subject_distribution = Column(JSONB, nullable=True)
    session_type = Column(String(20), default='standard', nullable=True)
    
    is_exam_mode = Column(Boolean, default=False, nullable=False)
    current_subject = Column(String(50), nullable=True)
    subject_order = Column(JSONB, nullable=True)
    time_per_subject = Column(Integer, default=3600, nullable=True)
    subject_times = Column(JSONB, nullable=True)
    
    time_limit = Column(Integer, default=60)
    time_limit_minutes = Column(Integer, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    time_spent = Column(Integer, nullable=True)
    
    user_answers = Column(JSONB, nullable=True)
    correct_count = Column(Integer, default=0)
    incorrect_count = Column(Integer, default=0)
    unanswered_count = Column(Integer, default=0)
    score = Column(Float, nullable=True)
    max_score = Column(Float, nullable=True)
    results = Column(JSONB, nullable=True)
    
    can_review = Column(Boolean, default=True, nullable=False)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    
    user = relationship("User", back_populates="sessions")

# ============================================================================
# USER PROGRESS MODEL
# ============================================================================

class UserProgress(Base):
    __tablename__ = "user_progress"
    
    user_id = Column(String(50), ForeignKey('users.user_id', ondelete='CASCADE'), primary_key=True)
    
    total_sessions = Column(Integer, default=0, nullable=False)
    total_questions = Column(Integer, default=0, nullable=False)
    total_correct = Column(Integer, default=0, nullable=False)
    overall_accuracy = Column(Float, default=0.0, nullable=False)
    
    subject_stats = Column(JSONB, nullable=True)
    difficulty_stats = Column(JSONB, nullable=True)
    mode_stats = Column(JSONB, nullable=True)
    
    best_score = Column(Float, default=0.0, nullable=False)
    best_session_id = Column(String(50), nullable=True)
    
    last_activity = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    
    user = relationship("User", back_populates="progress")

# ============================================================================
# AUDIT LOG MODEL
# ============================================================================

class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index('idx_audit_timestamp', 'timestamp'),
        Index('idx_audit_user', 'user_id'),
        Index('idx_audit_action', 'action'),
    )
    
    log_id = Column(String(50), primary_key=True, default=lambda: f"log_{uuid.uuid4().hex[:12]}")
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    
    action = Column(String(100), nullable=False)
    user_id = Column(String(50), nullable=True)
    performed_by = Column(String(50), nullable=True)
    
    details = Column(JSONB, nullable=True)
    ip_address = Column(String(50), nullable=True)
    success = Column(Boolean, default=True, nullable=False)
    error_message = Column(Text, nullable=True)

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_role_access_level(role: str) -> dict:
    """Get access level for each role"""
    access_levels = {
        'admin': {
            'can_access_cpns': True,
            'can_access_polri': True,
            'can_manage_users': True,
            'can_view_all_data': True,
            'can_upload_materials': True,
        },
        'user_cpns': {
            'can_access_cpns': True,
            'can_access_polri': False,
            'can_manage_users': False,
            'can_view_all_data': False,
            'can_upload_materials': False,
        },
        'user_polri': {
            'can_access_cpns': False,
            'can_access_polri': True,
            'can_manage_users': False,
            'can_view_all_data': False,
            'can_upload_materials': False,
        },
        'user_mixed': {
            'can_access_cpns': True,
            'can_access_polri': True,
            'can_manage_users': False,
            'can_view_all_data': False,
            'can_upload_materials': False,
        }
    }
    return access_levels.get(role, access_levels['user_cpns'])

def get_tier_features(tier: str) -> dict:
    """
    Get features available for each tier
    
    4-TIER SYSTEM:
    - admin: Full access + user management + no limits
    - premium: Exam mode + explanations + 200 questions
    - basic: Explanations + 50 questions + no exam
    - free: 10 questions + no exam + no explanations + 10 session limit
    """
    tier_features = {
        'admin': {
            'can_practice': True,
            'can_review': True,
            'can_exam_mode': True,
            'has_explanations': True,
            'has_statistics': True,
            'can_manage_users': True,
            'can_switch_branch': True,
            'max_questions_per_session': 999,
            'max_sessions': 999999,
            'tier_name': 'Administrator',
            'tier_emoji': '👔'
        },
        'premium': {
            'can_practice': True,
            'can_review': True,
            'can_exam_mode': True,
            'has_explanations': True,
            'has_statistics': True,
            'can_manage_users': False,
            'can_switch_branch': True,
            'max_questions_per_session': 200,
            'max_sessions': 999999,
            'tier_name': 'Premium',
            'tier_emoji': '⭐'
        },
        'basic': {
            'can_practice': True,
            'can_review': True,
            'can_exam_mode': False,
            'has_explanations': True,
            'has_statistics': True,
            'can_manage_users': False,
            'can_switch_branch': False,
            'max_questions_per_session': 50,
            'max_sessions': 999999,
            'tier_name': 'Basic',
            'tier_emoji': '📘'
        },
        'free': {
            'can_practice': True,
            'can_review': True,
            'can_exam_mode': False,
            'has_explanations': False,
            'has_statistics': False,
            'can_manage_users': False,
            'can_switch_branch': False,
            'max_questions_per_session': 10,
            'max_sessions': 10,
            'tier_name': 'Free',
            'tier_emoji': '🆓'
        }
    }
    return tier_features.get(tier, tier_features['free'])