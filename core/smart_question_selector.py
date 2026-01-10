"""
Smart Question Selector with Review Mode
NEW MODE: NEVER REPEATS (EVER!)
REVIEW MODE: Practice past questions anytime
"""

import sys
import os
from typing import List, Optional, Dict
from datetime import datetime, timezone
from sqlalchemy import and_, or_, func, not_

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models import Question, QuestionUsage, QuestionSession

class SmartQuestionSelector:
    """
    Enhanced question selection with:
    - NEW mode: NEVER repeats (shows each question only once EVER)
    - REVIEW mode: Shows past questions for practice
    """
    
    def __init__(self, db_session=None):
        self.db = db_session or SessionLocal()
        self.should_close = db_session is None
    
    def __del__(self):
        if self.should_close and self.db:
            self.db.close()
    
    def select_new_questions(
        self,
        user_id: str,
        test_category: str,
        subject: str,
        count: int,
        difficulty_distribution: Optional[Dict[str, int]] = None,
        subtype: Optional[str] = None
    ) -> Dict:
        """
        Select questions for NEW session
        GUARANTEES: NEVER shows same question twice (EVER!)
        
        Args:
            user_id: User ID
            test_category: polri/cpns
            subject: Subject area
            count: Total questions needed
            difficulty_distribution: Dict like {'mudah': 20, 'sedang': 20, 'sulit': 10}
            subtype: Optional subtype (for TIU)
            
        Returns:
            Dict with questions and availability stats
        """
        # Default distribution if not provided
        if not difficulty_distribution:
            difficulty_distribution = {
                'mudah': int(count * 0.4),    # 40% easy
                'sedang': int(count * 0.4),   # 40% medium
                'sulit': count - int(count * 0.4) - int(count * 0.4)  # 20% hard
            }
        
        # Get ALL questions user has EVER seen (no time limit!)
        used_questions = self.db.query(QuestionUsage.question_id).filter(
            QuestionUsage.user_id == user_id
        ).subquery()
        
        selected_questions = []
        availability_stats = {}
        
        # Select by difficulty
        for difficulty, needed_count in difficulty_distribution.items():
            # Build query - exclude ALL previously used questions
            query = self.db.query(Question).filter(
                and_(
                    Question.test_category == test_category,
                    Question.subject == subject,
                    Question.difficulty == difficulty,
                    ~Question.question_id.in_(used_questions.select())  # Never used by this user
                )
            )
            
            # Add subtype filter if specified
            if subtype:
                query = query.filter(Question.subtype == subtype)
            
            # Get available count
            available_count = query.count()
            availability_stats[difficulty] = {
                'needed': needed_count,
                'available': available_count
            }
            
            # Priority selection:
            # 1. Never used globally (usage_count = 0 or NULL)
            # 2. Least used globally (lowest usage_count)
            # 3. Random selection
            questions = query.order_by(
                func.coalesce(Question.usage_count, 0).asc(),
                func.random()
            ).limit(needed_count).all()
            
            selected_questions.extend(questions)
        
        # Check if we got enough questions
        total_available = sum(stat['available'] for stat in availability_stats.values())
        total_selected = len(selected_questions)
        
        return {
            'questions': selected_questions,
            'total_selected': total_selected,
            'total_needed': count,
            'is_sufficient': total_selected >= count,
            'availability_by_difficulty': availability_stats,
            'total_available': total_available,
            'can_create_session': total_selected >= count,
            'message': self._get_availability_message(
                total_selected, count, total_available
            )
        }
    
    def select_review_questions(
        self,
        user_id: str,
        original_session_id: str
    ) -> Dict:
        """
        Select questions for REVIEW mode
        Shows exact same questions from a past session
        
        Args:
            user_id: User ID
            original_session_id: ID of session to review
            
        Returns:
            Dict with questions from that session
        """
        # Get original session
        original_session = self.db.query(QuestionSession).filter(
            and_(
                QuestionSession.session_id == original_session_id,
                QuestionSession.user_id == user_id
            )
        ).first()
        
        if not original_session:
            return {
                'error': 'Session not found or not owned by user',
                'questions': []
            }
        
        # Get questions from that session (in same order)
        usage_records = self.db.query(QuestionUsage).filter(
            and_(
                QuestionUsage.session_id == original_session_id,
                QuestionUsage.user_id == user_id
            )
        ).order_by(QuestionUsage.usage_id).all()
        
        question_ids = [u.question_id for u in usage_records]
        
        # Get actual questions
        questions = self.db.query(Question).filter(
            Question.question_id.in_(question_ids)
        ).all()
        
        # Sort by original order
        question_dict = {q.question_id: q for q in questions}
        ordered_questions = [question_dict[qid] for qid in question_ids if qid in question_dict]
        
        # Get user's previous answers
        previous_answers = {}
        for usage in usage_records:
            previous_answers[usage.question_id] = {
                'user_answer': usage.user_answer,
                'was_correct': usage.was_correct,
                'time_spent': usage.time_spent
            }
        
        return {
            'questions': ordered_questions,
            'total_questions': len(ordered_questions),
            'original_session': {
                'session_id': original_session.session_id,
                'completed_at': original_session.completed_at,
                'score': original_session.score,
                'correct_count': original_session.correct_count,
                'total_questions': original_session.total_questions
            },
            'previous_answers': previous_answers,
            'is_review_mode': True
        }
    
    def get_available_question_count(
        self,
        user_id: str,
        test_category: str,
        subject: str,
        subtype: Optional[str] = None
    ) -> Dict:
        """
        Get count of available NEW questions for user
        (Questions they have NEVER seen)
        
        Returns:
            Dict with availability stats
        """
        # Get ALL questions user has ever seen
        used_questions = self.db.query(QuestionUsage.question_id).filter(
            QuestionUsage.user_id == user_id
        ).subquery()
        
        # Count by difficulty
        stats = {}
        total_available = 0
        
        for difficulty in ['mudah', 'sedang', 'sulit']:
            query = self.db.query(func.count(Question.question_id)).filter(
                and_(
                    Question.test_category == test_category,
                    Question.subject == subject,
                    Question.difficulty == difficulty,
                    ~Question.question_id.in_(used_questions.select())  # Never used
                )
            )
            
            if subtype:
                query = query.filter(Question.subtype == subtype)
            
            count = query.scalar()
            stats[difficulty] = count
            total_available += count
        
        return {
            'test_category': test_category,
            'subject': subject,
            'subtype': subtype,
            'by_difficulty': stats,
            'total_available': total_available,
            'can_create_50q_session': total_available >= 50
        }
    
    def mark_questions_used(
        self,
        question_ids: List[str],
        user_id: str,
        session_id: str
    ):
        """
        Mark questions as used
        Once marked, user will NEVER see them again in NEW mode
        
        Args:
            question_ids: List of question IDs
            user_id: User ID
            session_id: Session ID
        """
        now = datetime.now(timezone.utc)
        
        for q_id in question_ids:
            # Create usage record
            usage = QuestionUsage(
                question_id=q_id,
                user_id=user_id,
                session_id=session_id,
                used_at=now
            )
            self.db.add(usage)
            
            # Update question stats
            question = self.db.query(Question).filter(
                Question.question_id == q_id
            ).first()
            
            if question:
                question.is_used = True
                question.usage_count = (question.usage_count or 0) + 1
                question.last_used_at = now
        
        self.db.commit()
    
    def get_user_session_history(
        self,
        user_id: str,
        limit: int = 20
    ) -> List[Dict]:
        """
        Get user's past sessions for review
        
        Args:
            user_id: User ID
            limit: Max sessions to return
            
        Returns:
            List of session summaries
        """
        sessions = self.db.query(QuestionSession).filter(
            and_(
                QuestionSession.user_id == user_id,
                QuestionSession.status == 'completed'
            )
        ).order_by(
            QuestionSession.completed_at.desc()
        ).limit(limit).all()
        
        history = []
        for session in sessions:
            history.append({
                'session_id': session.session_id,
                'completed_at': session.completed_at,
                'test_category': session.test_category,
                'subject': session.subject,
                'session_type': session.session_type,
                'total_questions': session.total_questions,
                'correct_count': session.correct_count,
                'incorrect_count': session.incorrect_count,
                'score': session.score,
                'time_limit': session.time_limit,
                'can_review': True
            })
        
        return history
    
    def get_user_stats(self, user_id: str) -> Dict:
        """
        Get user's overall statistics
        
        Returns:
            Dict with user stats
        """
        # Total unique questions seen
        total_seen = self.db.query(func.count(func.distinct(QuestionUsage.question_id))).filter(
            QuestionUsage.user_id == user_id
        ).scalar()
        
        # Total answered
        total_answered = self.db.query(func.count(QuestionUsage.usage_id)).filter(
            and_(
                QuestionUsage.user_id == user_id,
                QuestionUsage.user_answered == True
            )
        ).scalar()
        
        # Total correct
        total_correct = self.db.query(func.count(QuestionUsage.usage_id)).filter(
            and_(
                QuestionUsage.user_id == user_id,
                QuestionUsage.was_correct == True
            )
        ).scalar()
        
        return {
            'total_questions_seen': total_seen or 0,
            'total_answered': total_answered or 0,
            'total_correct': total_correct or 0,
            'accuracy': (total_correct / total_answered * 100) if total_answered > 0 else 0
        }
    
    def _get_availability_message(
        self,
        selected: int,
        needed: int,
        available: int
    ) -> str:
        """Generate user-friendly availability message"""
        if selected >= needed:
            return f"✅ {selected} fresh questions available (never seen before)"
        elif available >= needed:
            return f"✅ {available} questions available (selected {selected})"
        else:
            shortage = needed - available
            return f"⚠️ Only {available} unused questions available. Need {shortage} more. Use Review Mode to practice past questions."


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def can_create_new_session(
    user_id: str,
    test_category: str,
    subject: str,
    count: int = 50
) -> Dict:
    """Check if user can create new session"""
    selector = SmartQuestionSelector()
    stats = selector.get_available_question_count(user_id, test_category, subject)
    
    return {
        'can_create': stats['total_available'] >= count,
        'available': stats['total_available'],
        'needed': count,
        'stats': stats
    }


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("  🧪 SMART QUESTION SELECTOR - NEVER REPEAT MODE")
    print("=" * 70 + "\n")
    
    from models import User
    
    selector = SmartQuestionSelector()
    
    # Test with first user
    user = selector.db.query(User).first()
    
    if user:
        print("1️⃣  Testing availability check...")
        stats = selector.get_available_question_count(
            user_id=user.user_id,
            test_category='cpns',
            subject='tiu'
        )
        print(f"   📊 Available (never seen): {stats['total_available']}")
        print(f"   📈 By difficulty: {stats['by_difficulty']}\n")
        
        print("2️⃣  Testing user stats...")
        user_stats = selector.get_user_stats(user.user_id)
        print(f"   📚 Questions seen (lifetime): {user_stats['total_questions_seen']}")
        print(f"   ✅ Correct answers: {user_stats['total_correct']}/{user_stats['total_answered']}")
        print(f"   🎯 Accuracy: {user_stats['accuracy']:.1f}%\n")
        
        print("3️⃣  Testing session history...")
        history = selector.get_user_session_history(user.user_id, limit=5)
        print(f"   📝 Found {len(history)} past sessions")
        
        if history:
            print(f"   📅 Latest: {history[0]['completed_at']}")
            print(f"   💯 Score: {history[0]['score']:.1f}%\n")
        else:
            print()
    else:
        print("⚠️  No users found in database\n")
    
    print("=" * 70)
    print("  ✅ SELECTOR READY!")
    print("=" * 70)
    print("\n🎯 Mode: NEVER REPEAT")
    print("   • NEW sessions: Each question shown only ONCE (forever)")
    print("   • REVIEW sessions: Practice past questions anytime")
    print("=" * 70 + "\n")