"""
Question Validator
Validate generated questions for quality and format
"""

import sys
import os
from typing import Dict, List, Tuple, Optional

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models import Question

class QuestionValidator:
    """
    Validate generated questions
    Check format, quality, and duplicates
    """
    
    def __init__(self):
        self.required_fields = [
            'question_text',
            'options',
            'correct_answer',
            'test_category',
            'subject',
            'difficulty'
        ]
        self.required_options = ['A', 'B', 'C', 'D', 'E']
        self.valid_difficulties = ['mudah', 'sedang', 'sulit']
        self.valid_categories = ['polri', 'cpns']
    
    def validate_question(self, question_data: Dict) -> Tuple[bool, List[str]]:
        """
        Validate a single question
        
        Args:
            question_data: Question dictionary
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Check required fields
        for field in self.required_fields:
            if field not in question_data:
                errors.append(f"Missing required field: {field}")
        
        if errors:
            return False, errors
        
        # Validate question text
        question_text = question_data.get('question_text', '')
        if not question_text or len(question_text.strip()) < 10:
            errors.append("Question text too short (minimum 10 characters)")
        
        if len(question_text) > 1000:
            errors.append("Question text too long (maximum 1000 characters)")
        
        # Validate options
        options = question_data.get('options', {})
        if not isinstance(options, dict):
            errors.append("Options must be a dictionary")
        else:
            # Check all required options exist
            for opt in self.required_options:
                if opt not in options:
                    errors.append(f"Missing option: {opt}")
                elif not options[opt] or len(str(options[opt]).strip()) < 1:
                    errors.append(f"Option {opt} is empty")
            
            # Check for duplicate options
            option_values = [str(v).strip().lower() for v in options.values()]
            if len(option_values) != len(set(option_values)):
                errors.append("Duplicate option values detected")
        
        # Validate correct answer
        correct_answer = question_data.get('correct_answer', '')
        if correct_answer not in self.required_options:
            errors.append(f"Invalid correct_answer: {correct_answer} (must be A, B, C, D, or E)")
        
        # Validate test category
        test_category = question_data.get('test_category', '')
        if test_category not in self.valid_categories:
            errors.append(f"Invalid test_category: {test_category} (must be polri or cpns)")
        
        # Validate difficulty
        difficulty = question_data.get('difficulty', '')
        if difficulty not in self.valid_difficulties:
            errors.append(f"Invalid difficulty: {difficulty} (must be mudah, sedang, or sulit)")
        
        # Validate explanation (optional but recommended)
        explanation = question_data.get('explanation', '')
        if explanation and len(explanation) > 2000:
            errors.append("Explanation too long (maximum 2000 characters)")
        
        return len(errors) == 0, errors
    
    def validate_batch(self, questions: List[Dict]) -> Dict:
        """
        Validate multiple questions
        
        Args:
            questions: List of question dictionaries
            
        Returns:
            Dict with validation results
        """
        results = {
            'total': len(questions),
            'valid': 0,
            'invalid': 0,
            'errors': {}
        }
        
        for i, question in enumerate(questions):
            is_valid, errors = self.validate_question(question)
            
            if is_valid:
                results['valid'] += 1
            else:
                results['invalid'] += 1
                results['errors'][i] = errors
        
        return results
    
    def check_duplicate(self, content_hash: str) -> bool:
        """
        Check if question with this hash already exists
        
        Args:
            content_hash: SHA256 hash of question content
            
        Returns:
            True if duplicate exists, False otherwise
        """
        db = SessionLocal()
        try:
            existing = db.query(Question).filter(
                Question.content_hash == content_hash
            ).first()
            
            return existing is not None
        finally:
            db.close()
    
    def check_duplicates_batch(self, questions: List[Dict]) -> Dict:
        """
        Check multiple questions for duplicates
        
        Args:
            questions: List of questions with content_hash
            
        Returns:
            Dict with duplicate info
        """
        results = {
            'total': len(questions),
            'duplicates': 0,
            'unique': 0,
            'duplicate_hashes': []
        }
        
        for question in questions:
            content_hash = question.get('content_hash')
            if not content_hash:
                continue
            
            if self.check_duplicate(content_hash):
                results['duplicates'] += 1
                results['duplicate_hashes'].append(content_hash)
            else:
                results['unique'] += 1
        
        return results
    
    def calculate_quality_score(self, question_data: Dict) -> float:
        """
        Calculate quality score for a question (0.0 to 1.0)
        
        Args:
            question_data: Question dictionary
            
        Returns:
            Quality score (0.0 to 1.0)
        """
        score = 1.0
        
        # Check question text length (optimal: 50-300 chars)
        q_text = question_data.get('question_text', '')
        q_len = len(q_text)
        if q_len < 20:
            score -= 0.2
        elif q_len < 50:
            score -= 0.1
        elif q_len > 500:
            score -= 0.2
        
        # Check if has explanation
        if not question_data.get('explanation'):
            score -= 0.2
        else:
            exp_len = len(question_data.get('explanation', ''))
            if exp_len < 20:
                score -= 0.1
            elif exp_len > 1000:
                score -= 0.1
        
        # Check option lengths (should be balanced)
        options = question_data.get('options', {})
        if options:
            opt_lengths = [len(str(v)) for v in options.values()]
            avg_length = sum(opt_lengths) / len(opt_lengths)
            
            # Penalize if one option is much longer (might give away answer)
            max_length = max(opt_lengths)
            if max_length > avg_length * 2:
                score -= 0.1
        
        # Ensure score is between 0 and 1
        return max(0.0, min(1.0, score))
    
    def filter_valid_questions(self, questions: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """
        Filter questions into valid and invalid lists
        
        Args:
            questions: List of question dictionaries
            
        Returns:
            Tuple of (valid_questions, invalid_questions)
        """
        valid = []
        invalid = []
        
        for question in questions:
            is_valid, errors = self.validate_question(question)
            
            if is_valid:
                # Add quality score
                question['quality_score'] = self.calculate_quality_score(question)
                valid.append(question)
            else:
                question['validation_errors'] = errors
                invalid.append(question)
        
        return valid, invalid


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def validate_question_data(question_data: Dict) -> Tuple[bool, List[str]]:
    """
    Convenience function to validate a question
    
    Args:
        question_data: Question dictionary
        
    Returns:
        Tuple of (is_valid, errors)
    """
    validator = QuestionValidator()
    return validator.validate_question(question_data)


def filter_duplicates(questions: List[Dict]) -> List[Dict]:
    """
    Filter out duplicate questions
    
    Args:
        questions: List of questions
        
    Returns:
        List of unique questions only
    """
    validator = QuestionValidator()
    unique = []
    
    for question in questions:
        content_hash = question.get('content_hash')
        if not content_hash:
            continue
        
        if not validator.check_duplicate(content_hash):
            unique.append(question)
    
    return unique


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    print("\n🧪 Testing Question Validator\n")
    
    # Test question 1: Valid
    valid_question = {
        'question_text': 'Apa sila pertama Pancasila?',
        'options': {
            'A': 'Ketuhanan Yang Maha Esa',
            'B': 'Kemanusiaan yang Adil dan Beradab',
            'C': 'Persatuan Indonesia',
            'D': 'Kerakyatan',
            'E': 'Keadilan Sosial'
        },
        'correct_answer': 'A',
        'explanation': 'Sila pertama Pancasila adalah Ketuhanan Yang Maha Esa.',
        'test_category': 'cpns',
        'subject': 'wawasan_kebangsaan',
        'difficulty': 'mudah',
        'content_hash': 'abc123'
    }
    
    # Test question 2: Invalid (missing field)
    invalid_question = {
        'question_text': 'Test?',
        'options': {
            'A': 'Option A',
            'B': 'Option B'
        },
        'correct_answer': 'A'
    }
    
    validator = QuestionValidator()
    
    # Test valid question
    print("1️⃣  Testing valid question...")
    is_valid, errors = validator.validate_question(valid_question)
    if is_valid:
        print("   ✅ Question is valid")
        quality = validator.calculate_quality_score(valid_question)
        print(f"   Quality score: {quality:.2f}")
    else:
        print(f"   ❌ Validation failed: {errors}")
    
    # Test invalid question
    print("\n2️⃣  Testing invalid question...")
    is_valid, errors = validator.validate_question(invalid_question)
    if is_valid:
        print("   ❌ Should have failed but passed!")
    else:
        print("   ✅ Correctly identified as invalid")
        print(f"   Errors found: {len(errors)}")
        for error in errors[:3]:  # Show first 3 errors
            print(f"     - {error}")
    
    # Test batch validation
    print("\n3️⃣  Testing batch validation...")
    batch = [valid_question, invalid_question, valid_question]
    results = validator.validate_batch(batch)
    print(f"   Total: {results['total']}")
    print(f"   ✅ Valid: {results['valid']}")
    print(f"   ❌ Invalid: {results['invalid']}")
    
    print("\n✅ Validator tests complete!\n")