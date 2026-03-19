"""
Question Selector
Smart question selection to prevent repeats and ensure variety
"""

import sys
import os
from typing import List, Optional
from datetime import datetime, timezone, timedelta
from sqlalchemy import and_, or_, func

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models import Question, QuestionUsage

class QuestionSelector:
    """
    Smart question selection system
    - Prevents showing same question to same user repeatedly
    - Prioritizes unused questions
    - Tracks usage statistics
    """
    
    def __init__(self, db_session=None):
        self.db = db_session or SessionLocal()
        self.should_close = db_session is None
    
    def __del__(self):
        if self.should_close and self.db:
            self.db.close()
    
    def select_for_session(
        self,
        user_id: str,
        test_category: str,
        subject: str,
        count: int,
        difficulty: Optional[str] = None,
        subtype: Optional[str] = None,
        exclude_recent_days: int = 30
    ) -> List[Question]:
        """
        Select questions for a user session
        
        Priority:
        1. Never used questions
        2. Least used questions
        3. Not shown to this user in last N days
        4. Oldest last_used_at
        
        Args:
            user_id: User ID
            test_category: polri or cpns
            subject: Subject area
            count: Number of questions needed
            difficulty: Optional difficulty filter
            subtype: Optional subtype filter
            exclude_recent_days: Don't show questions used in last N days
            
        Returns:
            List of selected Question objects
        """
        # Calculate cutoff date
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=exclude_recent_days)
        
        # Get questions this user has seen recently
        recent_usage = self.db.query(QuestionUsage.question_id).filter(
            and_(
                QuestionUsage.user_id == user_id,
                QuestionUsage.used_at >= cutoff_date
            )
        ).subquery()
        
        # Build main query
        query = self.db.query(Question).filter(
            and_(
                Question.test_category == test_category,
                Question.subject == subject,
                ~Question.question_id.in_(recent_usage)  # Exclude recent
            )
        )
        
        # Apply optional filters
        if difficulty:
            query = query.filter(Question.difficulty == difficulty)
        
        if subtype:
            query = query.filter(Question.subtype == subtype)
        
        # Order by priority:
        # 1. Never used (is_used = false) first
        # 2. Least used (lowest usage_count)
        # 3. Oldest used (oldest last_used_at or null)
        query = query.order_by(
            Question.is_used.asc(),           # False first (never used)
            Question.usage_count.asc(),        # Lowest count first
            Question.last_used_at.asc().nullsfirst()  # Oldest or never used
        )
        
        # Get questions
        questions = query.limit(count).all()
        
        return questions
    
    def mark_questions_used(
        self,
        question_ids: List[str],
        user_id: str,
        session_id: str
    ):
        """
        Mark questions as used in a session
        
        Args:
            question_ids: List of question IDs
            user_id: User ID
            session_id: Session ID
        """
        now = datetime.now(timezone.utc)
        
        for q_id in question_ids:
            # Update question usage stats
            question = self.db.query(Question).filter(
                Question.question_id == q_id
            ).first()
            
            if question:
                question.is_used = True
                question.usage_count = (question.usage_count or 0) + 1
                question.last_used_at = now
            
            # Record usage
            usage = QuestionUsage(
                question_id=q_id,
                user_id=user_id,
                session_id=session_id,
                used_at=now
            )
            self.db.add(usage)
        
        self.db.commit()
    
    def update_usage_results(
        self,
        question_id: str,
        user_id: str,
        session_id: str,
        was_correct: bool
    ):
        """
        Update usage record with answer result
        
        Args:
            question_id: Question ID
            user_id: User ID
            session_id: Session ID
            was_correct: Whether user answered correctly
        """
        usage = self.db.query(QuestionUsage).filter(
            and_(
                QuestionUsage.question_id == question_id,
                QuestionUsage.user_id == user_id,
                QuestionUsage.session_id == session_id
            )
        ).first()
        
        if usage:
            usage.user_answered = True
            usage.was_correct = was_correct
            self.db.commit()
    
    def get_usage_stats(self, question_id: str) -> dict:
        """
        Get usage statistics for a question
        
        Args:
            question_id: Question ID
            
        Returns:
            Dict with usage stats
        """
        question = self.db.query(Question).filter(
            Question.question_id == question_id
        ).first()
        
        if not question:
            return {}
        
        # Get detailed stats from usage records
        total_uses = self.db.query(QuestionUsage).filter(
            QuestionUsage.question_id == question_id
        ).count()
        
        answered = self.db.query(QuestionUsage).filter(
            and_(
                QuestionUsage.question_id == question_id,
                QuestionUsage.user_answered == True
            )
        ).count()
        
        correct = self.db.query(QuestionUsage).filter(
            and_(
                QuestionUsage.question_id == question_id,
                QuestionUsage.was_correct == True
            )
        ).count()
        
        return {
            'question_id': question_id,
            'is_used': question.is_used,
            'usage_count': question.usage_count or 0,
            'last_used_at': question.last_used_at,
            'total_sessions': total_uses,
            'answered_count': answered,
            'correct_count': correct,
            'correct_rate': correct / answered if answered > 0 else 0.0
        }
    
    def get_available_count(
        self,
        user_id: str,
        test_category: str,
        subject: str,
        difficulty: Optional[str] = None,
        exclude_recent_days: int = 30
    ) -> int:
        """
        Get count of available questions for user
        
        Args:
            user_id: User ID
            test_category: Test category
            subject: Subject
            difficulty: Optional difficulty
            exclude_recent_days: Exclude questions used in last N days
            
        Returns:
            Count of available questions
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=exclude_recent_days)
        
        recent_usage = self.db.query(QuestionUsage.question_id).filter(
            and_(
                QuestionUsage.user_id == user_id,
                QuestionUsage.used_at >= cutoff_date
            )
        ).subquery()
        
        query = self.db.query(func.count(Question.question_id)).filter(
            and_(
                Question.test_category == test_category,
                Question.subject == subject,
                ~Question.question_id.in_(recent_usage)
            )
        )
        
        if difficulty:
            query = query.filter(Question.difficulty == difficulty)
        
        return query.scalar()


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def select_questions_for_user(
    user_id: str,
    test_category: str,
    subject: str,
    count: int,
    difficulty: Optional[str] = None
) -> List[Question]:
    """
    Convenience function to select questions
    
    Args:
        user_id: User ID
        test_category: Test category
        subject: Subject
        count: Number of questions
        difficulty: Optional difficulty
        
    Returns:
        List of Question objects
    """
    selector = QuestionSelector()
    questions = selector.select_for_session(
        user_id,
        test_category,
        subject,
        count,
        difficulty
    )
    return questions


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    print("\n🧪 Testing Question Selector\n")
    
    from models import User
    
    selector = QuestionSelector()
    
    # Test 1: Get available count
    print("1️⃣  Testing available question count...")
    try:
        # Get a user
        user = selector.db.query(User).first()
        if user:
            count = selector.get_available_count(
                user_id=user.user_id,
                test_category='cpns',
                subject='tiu'
            )
            print(f"   ✅ Available questions: {count}")
        else:
            print("   ⚠️  No users found, skipping test")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 2: Select questions
    print("\n2️⃣  Testing question selection...")
    try:
        if user:
            questions = selector.select_for_session(
                user_id=user.user_id,
                test_category='cpns',
                subject='tiu',
                count=5,
                difficulty='mudah'
            )
            print(f"   ✅ Selected {len(questions)} questions")
            
            if questions:
                print(f"   First question: {questions[0].question_id}")
                print(f"   Usage count: {questions[0].usage_count}")
                print(f"   Is used: {questions[0].is_used}")
        else:
            print("   ⚠️  No users found, skipping test")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 3: Usage stats
    print("\n3️⃣  Testing usage statistics...")
    try:
        # Get a question
        question = selector.db.query(Question).first()
        if question:
            stats = selector.get_usage_stats(question.question_id)
            print(f"   ✅ Question: {question.question_id}")
            print(f"   Usage count: {stats.get('usage_count', 0)}")
            print(f"   Correct rate: {stats.get('correct_rate', 0):.1%}")
        else:
            print("   ⚠️  No questions found, skipping test")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print("\n✅ Selector tests complete!\n")