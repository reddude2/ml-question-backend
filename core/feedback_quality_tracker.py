"""
Feedback Quality Tracker
Track question performance based on user answers
Auto-retire low-performing questions
"""

import sys
import os
from typing import Dict, List, Optional
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models import Question, QuestionUsage

class FeedbackQualityTracker:
    """
    Track question quality based on user feedback
    Identify and retire poor-performing questions
    """
    
    def __init__(self, db_session=None):
        self.db = db_session or SessionLocal()
        self.should_close = db_session is None
        
        # Thresholds
        self.min_usage_for_evaluation = 10
        self.min_correct_rate = 0.30  # 30%
        self.max_correct_rate = 0.95  # 95%
    
    def __del__(self):
        if self.should_close and self.db:
            self.db.close()
    
    def update_question_statistics(self, question_id: str):
        """
        Update question statistics based on usage history
        
        Args:
            question_id: Question ID to update
        """
        question = self.db.query(Question).filter(
            Question.question_id == question_id
        ).first()
        
        if not question:
            return
        
        # Get usage statistics
        usage_records = self.db.query(QuestionUsage).filter(
            QuestionUsage.question_id == question_id,
            QuestionUsage.user_answered == True
        ).all()
        
        if not usage_records:
            return
        
        # Calculate correct rate
        total_answered = len(usage_records)
        total_correct = sum(1 for u in usage_records if u.was_correct)
        
        correct_rate = total_correct / total_answered if total_answered > 0 else 0.0
        
        # Update question
        question.usage_count = total_answered
        question.correct_rate = correct_rate
        
        self.db.commit()
    
    def evaluate_question_performance(self, question_id: str) -> Dict:
        """
        Evaluate if question should be retired
        
        Args:
            question_id: Question ID
            
        Returns:
            Dict with evaluation results
        """
        question = self.db.query(Question).filter(
            Question.question_id == question_id
        ).first()
        
        if not question:
            return {'error': 'Question not found'}
        
        # Update statistics first
        self.update_question_statistics(question_id)
        
        # Get updated question
        question = self.db.query(Question).filter(
            Question.question_id == question_id
        ).first()
        
        evaluation = {
            'question_id': question_id,
            'usage_count': question.usage_count or 0,
            'correct_rate': question.correct_rate or 0.0,
            'quality_score': question.quality_score or 0.0,
            'should_retire': False,
            'reasons': []
        }
        
        # Need minimum usage to evaluate
        if evaluation['usage_count'] < self.min_usage_for_evaluation:
            evaluation['status'] = 'insufficient_data'
            evaluation['reasons'].append(
                f"Need {self.min_usage_for_evaluation - evaluation['usage_count']} more uses"
            )
            return evaluation
        
        # Check if too difficult (too low correct rate)
        if evaluation['correct_rate'] < self.min_correct_rate:
            evaluation['should_retire'] = True
            evaluation['reasons'].append(
                f"Too difficult: {evaluation['correct_rate']:.1%} correct (min {self.min_correct_rate:.0%})"
            )
            evaluation['status'] = 'too_difficult'
        
        # Check if too easy (too high correct rate)
        elif evaluation['correct_rate'] > self.max_correct_rate:
            evaluation['should_retire'] = True
            evaluation['reasons'].append(
                f"Too easy: {evaluation['correct_rate']:.1%} correct (max {self.max_correct_rate:.0%})"
            )
            evaluation['status'] = 'too_easy'
        
        # Check quality score
        elif evaluation['quality_score'] < 0.60:
            evaluation['should_retire'] = True
            evaluation['reasons'].append(
                f"Low quality score: {evaluation['quality_score']:.2f}"
            )
            evaluation['status'] = 'low_quality'
        
        else:
            evaluation['status'] = 'performing_well'
        
        return evaluation
    
    def get_questions_to_retire(self) -> List[Dict]:
        """
        Get list of questions that should be retired
        
        Returns:
            List of questions with retirement reasons
        """
        # Get questions with sufficient usage
        questions = self.db.query(Question).filter(
            Question.usage_count >= self.min_usage_for_evaluation
        ).all()
        
        to_retire = []
        
        for question in questions:
            evaluation = self.evaluate_question_performance(question.question_id)
            
            if evaluation.get('should_retire'):
                to_retire.append({
                    'question_id': question.question_id,
                    'question_text': question.question_text[:50] + '...',
                    'usage_count': evaluation['usage_count'],
                    'correct_rate': evaluation['correct_rate'],
                    'quality_score': evaluation['quality_score'],
                    'reasons': evaluation['reasons'],
                    'status': evaluation['status']
                })
        
        return to_retire
    
    def retire_question(self, question_id: str, reason: str):
        """
        Retire a question (mark as inactive)
        
        Args:
            question_id: Question ID
            reason: Retirement reason
        """
        # For now, we'll add a note to explanation
        # In future, add 'is_active' field to Question model
        question = self.db.query(Question).filter(
            Question.question_id == question_id
        ).first()
        
        if question:
            # Add retirement note to explanation
            if question.explanation:
                question.explanation += f"\n\n[RETIRED: {reason}]"
            else:
                question.explanation = f"[RETIRED: {reason}]"
            
            # Lower quality score
            question.quality_score = 0.0
            
            self.db.commit()
    
    def get_performance_report(self) -> Dict:
        """
        Get overall performance report
        
        Returns:
            Dict with performance statistics
        """
        # Get all questions with usage
        questions = self.db.query(Question).filter(
            Question.usage_count > 0
        ).all()
        
        if not questions:
            return {'message': 'No questions with usage data'}
        
        total = len(questions)
        with_sufficient_data = len([q for q in questions if (q.usage_count or 0) >= self.min_usage_for_evaluation])
        
        avg_correct_rate = sum(q.correct_rate or 0 for q in questions) / total
        avg_quality_score = sum(q.quality_score or 0 for q in questions) / total
        
        # Performance categories
        excellent = len([q for q in questions if (q.correct_rate or 0) >= 0.70 and (q.correct_rate or 0) <= 0.85])
        too_easy = len([q for q in questions if (q.correct_rate or 0) > self.max_correct_rate])
        too_difficult = len([q for q in questions if (q.correct_rate or 0) < self.min_correct_rate and (q.usage_count or 0) >= self.min_usage_for_evaluation])
        
        return {
            'total_questions': total,
            'with_sufficient_data': with_sufficient_data,
            'avg_correct_rate': avg_correct_rate,
            'avg_quality_score': avg_quality_score,
            'excellent_questions': excellent,
            'too_easy': too_easy,
            'too_difficult': too_difficult,
            'needs_retirement': too_easy + too_difficult
        }


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    print("\n🧪 Testing Feedback Quality Tracker\n")
    
    tracker = FeedbackQualityTracker()
    
    print("1️⃣  Getting performance report...")
    report = tracker.get_performance_report()
    
    if 'message' in report:
        print(f"   ℹ️  {report['message']}")
    else:
        print(f"   Total questions: {report['total_questions']}")
        print(f"   With sufficient data: {report['with_sufficient_data']}")
        print(f"   Average correct rate: {report['avg_correct_rate']:.1%}")
        print(f"   Excellent questions: {report['excellent_questions']}")
        print(f"   Too easy: {report['too_easy']}")
        print(f"   Too difficult: {report['too_difficult']}")
    
    print("\n2️⃣  Checking for questions to retire...")
    to_retire = tracker.get_questions_to_retire()
    
    if to_retire:
        print(f"   Found {len(to_retire)} questions to retire:")
        for q in to_retire[:3]:  # Show first 3
            print(f"   - {q['question_id']}: {q['status']}")
            print(f"     Correct rate: {q['correct_rate']:.1%}")
    else:
        print("   ✅ No questions need retirement")
    
    print("\n✅ Tracker tests complete!\n")