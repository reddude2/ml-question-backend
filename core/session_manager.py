"""
Session Manager
Manage session lifecycle with NEW and REVIEW modes
"""

import sys
import os
from typing import Dict, List, Optional
from datetime import datetime, timezone
import secrets
import random

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models import QuestionSession, QuestionUsage, Question
from core.smart_question_selector import SmartQuestionSelector
from config import TES_POLRI, TES_CPNS
from sqlalchemy import and_, func, case

class SessionManager:
    """
    Manage user sessions with:
    - NEW mode: Fresh questions
    - REVIEW mode: Repeat past questions
    """
    
    def __init__(self, db_session=None):
        self.db = db_session or SessionLocal()
        self.should_close = db_session is None
        self.selector = SmartQuestionSelector(db_session=self.db)
    
    def __del__(self):
        # Fix: Check hasattr to avoid error if init failed
        if hasattr(self, 'should_close') and self.should_close and hasattr(self, 'db') and self.db:
            self.db.close()
    
    def create_new_session(
        self,
        user_id: str,
        session_type: str,  # practice/exam
        test_category: str,  # polri/cpns
        subject: str,
        count: Optional[int] = None,
        subtype: Optional[str] = None,
        difficulty_distribution: Optional[Dict[str, int]] = None
    ) -> Dict:
        """
        Create NEW session with fresh questions.
        FIX: Added Backfill Strategy (Recycle old questions if new ones run out).
        MODIFIED: Added conditional checks to skip Phase 2 & 3 if Phase 1 is sufficient.
        """
        # Get default count from config if not specified
        if count is None:
            count = self._get_default_question_count(test_category, subject)
        
        # Get time limit from config
        time_limit = self._get_time_limit(test_category, subject)
        
        # --- 1. PRIMARY SELECTION (Prioritas: Hard New) ---
        # Kita coba minta soal HARD yang BARU dulu sesuai settingan
        forced_distribution = {'hard': count}

        selection_result = self.selector.select_new_questions(
            user_id=user_id,
            test_category=test_category,
            subject=subject,
            count=count,
            difficulty_distribution=forced_distribution, 
            subtype=subtype
        )
        
        current_questions = selection_result['questions']
        
        # --- 2. SECONDARY FALLBACK (Sisa Stok Baru: Any Difficulty) ---
        # MODIFIED: Hanya jalan jika Fase 1 tidak cukup
        if len(current_questions) < count:
            needed = count - len(current_questions)
            # print(f"⚠️ Primary selection insufficient ({len(current_questions)}/{count}). Trying mixed difficulty...")

            exclude_ids = [q.question_id for q in current_questions]
            
            # difficulty_distribution=None artinya "AMBIL APA SAJA ASAL BARU"
            fallback_result = self.selector.select_new_questions(
                user_id=user_id,
                test_category=test_category,
                subject=subject,
                count=needed,
                difficulty_distribution=None, 
                subtype=subtype
            )
            
            # Gabungkan soal
            for q in fallback_result['questions']:
                if q.question_id not in exclude_ids:
                    current_questions.append(q)
                    exclude_ids.append(q.question_id)
            
            # Update total available info
            selection_result['total_available'] = len(current_questions)

        # --- 3. TERTIARY BACKFILL (Ambil Soal Lama/Recycle) ---
        # MODIFIED: Hanya jalan jika Fase 1 + Fase 2 masih tidak cukup
        if len(current_questions) < count:
            needed = count - len(current_questions)
            print(f"⚠️ Stock 'NEW' empty. Recycling {needed} old questions to fill session...")
            
            exclude_ids = [q.question_id for q in current_questions]
            
            old_questions = self._get_recycle_questions(
                test_category=test_category,
                subject=subject,
                count=needed,
                exclude_ids=exclude_ids,
                subtype=subtype
            )
            
            current_questions.extend(old_questions)

        # 4. Final Validation (Jika Database Kosong Melompong)
        if not current_questions:
            real_avail = selection_result.get('total_available', 0)
            return {
                'success': False,
                'error': 'insufficient_questions',
                'message': f"Database kosong untuk mapel ini. Mohon input soal master terlebih dahulu.",
                'available': real_avail,
                'needed': count
            }
        
        # Acak urutan soal gabungan (Baru + Lama)
        random.shuffle(current_questions)

        # Prepare questions data for database
        questions_data = []
        for q in current_questions:
            questions_data.append({
                'question_id': q.question_id,
                'question_text': q.question_text,
                'options': q.options,
                'difficulty': q.difficulty,
                'correct_answer': q.correct_answer,
                'explanation': q.explanation, # Pastikan explanation ikut tersimpan
                'answer_scores': getattr(q, 'answer_scores', None) # Untuk TKP
            })
        
        # --- FIX UTAMA: MAPPING KE CONSTRAINT DB ---
        # Database Anda MENOLAK 'practice' pada kolom session_type.
        # Database hanya menerima: 'standard' atau 'exam'.
        
        db_session_type = 'standard' # Default mapping: practice -> standard
        if session_type == 'exam':
            db_session_type = 'exam'
            
        # Database Anda MENOLAK 'new' pada kolom mode.
        # Database hanya menerima: 'practice', 'review', 'exam'.
        db_mode = 'practice' # Default mapping
        if session_type == 'exam':
            db_mode = 'exam'
        
        # Create session
        session_id = self._generate_session_id()
        
        session = QuestionSession(
            session_id=session_id,
            user_id=user_id,
            test_category=test_category,
            difficulty='mixed', # Karena bisa campuran
            total_questions=len(questions_data),
            questions_data=questions_data,
            
            # FIX: Status awal HARUS 'created' (agar tombol Start di frontend aktif)
            status='created', 
            
            # FIX: Gunakan nilai hasil mapping yang valid di DB
            mode=db_mode, 
            session_type=db_session_type,
            
            subject=subject,
            subtype=subtype,
            time_limit=time_limit,
            time_limit_minutes=time_limit,
            created_at=datetime.now(timezone.utc), # Created at setting
            correct_count=0,
            incorrect_count=0,
            unanswered_count=len(questions_data),
            is_exam_mode=(session_type == 'exam'),
            can_review=True
        )
        
        # MODIFIED: Menambahkan sesi ke database tanpa langsung commit
        self.db.add(session)
        
        # Mark NEW questions as used (Old ones are already used, re-marking is fine)
        # MODIFIED: Pindahkan ke sini agar dieksekusi sebelum commit akhir
        question_ids = [q.question_id for q in current_questions]
        self.selector.mark_questions_used(question_ids, user_id, session_id)
        
        # Final Commit (Menyimpan sesi dan penggunaan soal sekaligus)
        self.db.commit()
        
        return {
            'success': True,
            'session_id': session_id,
            'session_type': session_type, # Return type asli ke frontend
            'test_category': test_category,
            'subject': subject,
            'total_questions': len(questions_data),
            'time_limit': time_limit,
            'questions': self._format_questions_for_session(current_questions),
            'started_at': None # Belum start
        }
    
    def create_review_session(
        self,
        user_id: str,
        original_session_id: str
    ) -> Dict:
        """
        Create REVIEW session from past session
        """
        # Get questions from original session
        review_result = self.selector.select_review_questions(
            user_id=user_id,
            original_session_id=original_session_id
        )
        
        if 'error' in review_result:
            return {
                'success': False,
                'error': review_result['error']
            }
        
        # Get original session object
        original_obj = self.db.query(QuestionSession).filter(
            QuestionSession.session_id == original_session_id
        ).first()
        
        if not original_obj:
            return {
                'success': False,
                'error': 'Original session not found'
            }
        
        # Prepare questions data
        questions_data = []
        for q in review_result['questions']:
            questions_data.append({
                'question_id': q.question_id,
                'question_text': q.question_text,
                'options': q.options,
                'difficulty': q.difficulty,
                'correct_answer': q.correct_answer,
                'explanation': q.explanation
            })
        
        # Create review session
        session_id = self._generate_session_id()
        
        session = QuestionSession(
            session_id=session_id,
            user_id=user_id,
            test_category=original_obj.test_category,
            difficulty=original_obj.difficulty,
            total_questions=review_result['total_questions'],
            questions_data=questions_data,
            
            # FIX: Status 'created'
            status='created',
            
            # FIX: Mode review, Session type standard (agar valid di DB)
            mode='review',
            session_type='standard',
            
            subject=original_obj.subject,
            subtype=original_obj.subtype,
            time_limit=original_obj.time_limit,
            time_limit_minutes=original_obj.time_limit_minutes,
            created_at=datetime.now(timezone.utc),
            correct_count=0,
            incorrect_count=0,
            unanswered_count=review_result['total_questions'],
            is_exam_mode=False,
            can_review=True
        )
        
        self.db.add(session)
        
        # Create usage records
        for q in review_result['questions']:
            usage = QuestionUsage(
                question_id=q.question_id,
                user_id=user_id,
                session_id=session_id,
                used_at=datetime.now(timezone.utc),
                user_answered=False, 
                was_correct=False 
            )
            self.db.add(usage)
        
        self.db.commit()
        
        return {
            'success': True,
            'session_id': session_id,
            'session_type': 'review',
            'is_review_mode': True,
            'original_session_id': original_session_id,
            'original_completed_at': review_result['original_session']['completed_at'],
            'original_score': review_result['original_session']['score'],
            'total_questions': review_result['total_questions'],
            'time_limit': original_obj.time_limit,
            'questions': self._format_questions_for_session(
                review_result['questions'],
                previous_answers=review_result.get('previous_answers')
            ),
            'started_at': None
        }
    
    def submit_answer(
        self,
        session_id: str,
        question_id: str,
        user_answer: str,
        time_spent: Optional[int] = None
    ) -> Dict:
        """
        Submit answer for a question in session
        """
        # Get question
        question = self.db.query(Question).filter(
            Question.question_id == question_id
        ).first()
        
        if not question:
            return {
                'success': False,
                'error': 'question_not_found'
            }
        
        # Check answer
        is_correct = user_answer == question.correct_answer
        
        # Update usage record
        usage = self.db.query(QuestionUsage).filter(
            and_(
                QuestionUsage.session_id == session_id,
                QuestionUsage.question_id == question_id
            )
        ).first()
        
        if usage:
            usage.user_answered = True
            usage.user_answer = user_answer
            usage.was_correct = is_correct
            if time_spent is not None:
                usage.time_spent = time_spent
            
            self.db.commit()
        
        return {
            'success': True,
            'is_correct': is_correct,
            'correct_answer': question.correct_answer,
            'explanation': question.explanation
        }
    
    def complete_session(
        self,
        session_id: str
    ) -> Dict:
        """
        Complete session and calculate final score
        """
        # Get session
        session = self.db.query(QuestionSession).filter(
            QuestionSession.session_id == session_id
        ).first()
        
        if not session:
            return {
                'success': False,
                'error': 'session_not_found'
            }
        
        # Get all answers
        usage_records = self.db.query(QuestionUsage).filter(
            QuestionUsage.session_id == session_id
        ).all()
        
        # Calculate results
        correct_count = sum(1 for u in usage_records if u.was_correct)
        incorrect_count = sum(1 for u in usage_records if u.user_answered and not u.was_correct)
        
        # Fix: Unanswered count
        unanswered_count = session.total_questions - (correct_count + incorrect_count)
        if unanswered_count < 0: unanswered_count = 0
        
        # Calculate score (percentage)
        score = (correct_count / session.total_questions * 100) if session.total_questions > 0 else 0
        
        # Update session
        session.status = 'completed'
        session.completed_at = datetime.now(timezone.utc)
        session.correct_count = correct_count
        session.incorrect_count = incorrect_count
        session.unanswered_count = unanswered_count
        session.score = score
        
        self.db.commit()
        
        # Update question statistics (correct_rate)
        unique_question_ids = list(set(u.question_id for u in usage_records if u.user_answered))
        
        for q_id in unique_question_ids:
            stats = self.db.query(
                func.count(QuestionUsage.usage_id).label('total'),
                func.sum(case((QuestionUsage.was_correct == True, 1), else_=0)).label('correct')
            ).filter(
                QuestionUsage.question_id == q_id,
                QuestionUsage.user_answered == True
            ).first()
            
            if stats and stats.total > 0:
                new_rate = stats.correct / stats.total
                self.db.query(Question).filter(
                    Question.question_id == q_id
                ).update({'correct_rate': new_rate})

        self.db.commit()
        
        return {
            'success': True,
            'session_id': session_id,
            'status': 'completed',
            'total_questions': session.total_questions,
            'correct_count': correct_count,
            'incorrect_count': incorrect_count,
            'unanswered_count': unanswered_count,
            'score': score,
            'completed_at': session.completed_at
        }
    
    def get_session_results(
        self,
        session_id: str,
        include_questions: bool = False
    ) -> Dict:
        """
        Get detailed session results
        """
        session = self.db.query(QuestionSession).filter(
            QuestionSession.session_id == session_id
        ).first()
        
        if not session:
            return {
                'success': False,
                'error': 'session_not_found'
            }
        
        result = {
            'success': True,
            'session_id': session_id,
            'session_type': session.session_type,
            'test_category': session.test_category,
            'subject': session.subject,
            'total_questions': session.total_questions,
            'correct_count': session.correct_count,
            'incorrect_count': session.incorrect_count,
            'unanswered_count': session.unanswered_count,
            'score': session.score,
            'time_limit': session.time_limit,
            'started_at': session.started_at,
            'completed_at': session.completed_at,
            'status': session.status
        }
        
        if include_questions:
            usage_records = self.db.query(QuestionUsage).filter(
                QuestionUsage.session_id == session_id
            ).order_by(QuestionUsage.usage_id).all()
            
            q_ids = [u.question_id for u in usage_records]
            
            questions_map = {}
            if q_ids:
                questions = self.db.query(Question).filter(
                    Question.question_id.in_(q_ids)
                ).all()
                questions_map = {q.question_id: q for q in questions}
            
            questions_details = []
            for usage in usage_records:
                question = questions_map.get(usage.question_id)
                
                if question:
                    questions_details.append({
                        'question_id': question.question_id,
                        'question_text': question.question_text,
                        'options': question.options,
                        'correct_answer': question.correct_answer,
                        'user_answer': usage.user_answer,
                        'was_correct': usage.was_correct,
                        'explanation': question.explanation,
                        'time_spent': usage.time_spent
                    })
            
            result['questions'] = questions_details
        
        return result
    
    def _get_recycle_questions(self, test_category: str, subject: str, count: int, exclude_ids: List[str], subtype: Optional[str] = None):
        """
        Helper untuk mengambil soal lama secara acak (Backfill)
        tanpa mempedulikan status usage.
        """
        query = self.db.query(Question).filter(
            Question.test_category == test_category,
            Question.subject == subject,
            ~Question.question_id.in_(exclude_ids)
        )
        
        if subtype:
            query = query.filter(Question.subtype == subtype)
            
        return query.order_by(func.random()).limit(count).all()

    def _get_default_question_count(self, test_category: str, subject: str) -> int:
        """Get default question count from config"""
        if test_category == 'polri':
            return TES_POLRI.get(subject, {}).get('count', 50)
        elif test_category == 'cpns':
            return TES_CPNS.get(subject, {}).get('count', 30)
        return 50
    
    def _get_time_limit(self, test_category: str, subject: str) -> int:
        """Get time limit from config (in minutes)"""
        if test_category == 'polri':
            return TES_POLRI.get(subject, {}).get('time', 60)
        elif test_category == 'cpns':
            return TES_CPNS.get(subject, {}).get('time', 40)
        return 60
    
    def _generate_session_id(self) -> str:
        """Generate unique session ID"""
        return f"session_{secrets.token_hex(8)}"
    
    def _format_questions_for_session(
        self,
        questions: List[Question],
        previous_answers: Optional[Dict] = None
    ) -> List[Dict]:
        """Format questions for API response"""
        formatted = []
        
        for i, q in enumerate(questions, 1):
            question_dict = {
                'order': i,
                'question_id': q.question_id,
                'question_text': q.question_text,
                'options': q.options,
                'difficulty': q.difficulty
            }
            
            if previous_answers and q.question_id in previous_answers:
                prev = previous_answers[q.question_id]
                question_dict['previous_answer'] = {
                    'user_answer': prev['user_answer'],
                    'was_correct': prev['was_correct'],
                    'time_spent': prev['time_spent']
                }
            
            formatted.append(question_dict)
        
        return formatted


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    print("\n🧪 Testing Session Manager\n")
    
    from models import User
    
    manager = SessionManager()
    
    # Test with first user
    user = manager.db.query(User).first()
    
    if user:
        print("1️⃣  Testing session creation availability...")
        selector = SmartQuestionSelector(db_session=manager.db)
        stats = selector.get_available_question_count(
            user_id=user.user_id,
            test_category='cpns',
            subject='tiu'
        )
        print(f"   Available: {stats['total_available']} questions")
        
        if stats['total_available'] >= 5:
            print("\n2️⃣  Creating test session...")
            result = manager.create_new_session(
                user_id=user.user_id,
                session_type='practice',
                test_category='cpns',
                subject='tiu',
                count=5
            )
            
            if result['success']:
                print(f"   ✅ Session created: {result['session_id']}")
                print(f"   Questions: {result['total_questions']}")
                print(f"   Time limit: {result['time_limit']} minutes")
            else:
                print(f"   ❌ Failed: {result.get('message', result.get('error'))}")
        else:
            print("\n   ⚠️  Not enough questions for test session")
        
        print("\n3️⃣  Testing session history...")
        history = selector.get_user_session_history(user.user_id, limit=5)
        print(f"   Found {len(history)} past sessions")
        
    else:
        print("⚠️  No users found in database")
    
    print("\n✅ Session Manager ready.")