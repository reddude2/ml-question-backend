"""
Advanced Quality Controller
Strict quality control for generated questions
"""

import sys
import os
from typing import Dict, List, Tuple, Optional
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.question_validator import QuestionValidator

class QualityController(QuestionValidator):
    """
    Advanced quality control with stricter rules
    Ensures only HIGH-QUALITY questions pass
    """
    
    def __init__(self, min_quality_score: float = 0.7):
        super().__init__()
        self.min_quality_score = min_quality_score
        
        # Quality rules
        self.min_question_length = 20
        self.max_question_length = 500
        self.min_explanation_length = 30
        self.min_option_length = 3
        self.max_option_length = 200
    
    def deep_quality_check(self, question_data: Dict) -> Tuple[bool, float, List[str]]:
        """
        Comprehensive quality check
        
        Returns:
            Tuple of (passes, quality_score, issues)
        """
        issues = []
        
        # Basic validation first
        is_valid, errors = self.validate_question(question_data)
        if not is_valid:
            return False, 0.0, errors
        
        # Calculate quality score
        quality_score = self.calculate_advanced_quality_score(question_data)
        
        # Check against minimum threshold
        if quality_score < self.min_quality_score:
            issues.append(f"Quality score {quality_score:.2f} below threshold {self.min_quality_score}")
        
        # Detailed quality checks
        issues.extend(self._check_question_quality(question_data))
        issues.extend(self._check_options_quality(question_data))
        issues.extend(self._check_explanation_quality(question_data))
        issues.extend(self._check_answer_distribution(question_data))
        
        passes = len(issues) == 0 and quality_score >= self.min_quality_score
        
        return passes, quality_score, issues
    
    def calculate_advanced_quality_score(self, question_data: Dict) -> float:
        """
        Advanced quality scoring (0.0 to 1.0)
        More strict than basic validator
        """
        score = 1.0
        penalties = []
        
        # 1. Question Text Quality (30% weight)
        q_text = question_data.get('question_text', '')
        q_score = self._score_question_text(q_text)
        score -= (1 - q_score) * 0.3
        if q_score < 0.7:
            penalties.append(f"Question text quality: {q_score:.2f}")
        
        # 2. Options Quality (30% weight)
        options = question_data.get('options', {})
        opt_score = self._score_options(options)
        score -= (1 - opt_score) * 0.3
        if opt_score < 0.7:
            penalties.append(f"Options quality: {opt_score:.2f}")
        
        # 3. Explanation Quality (25% weight)
        explanation = question_data.get('explanation', '')
        exp_score = self._score_explanation(explanation)
        score -= (1 - exp_score) * 0.25
        if exp_score < 0.7:
            penalties.append(f"Explanation quality: {exp_score:.2f}")
        
        # 4. Answer Distribution (15% weight)
        correct_answer = question_data.get('correct_answer', '')
        dist_score = self._score_answer_distribution(correct_answer, options)
        score -= (1 - dist_score) * 0.15
        
        return max(0.0, min(1.0, score))
    
    def _score_question_text(self, text: str) -> float:
        """Score question text quality (0-1)"""
        score = 1.0
        
        # Length check
        length = len(text)
        if length < self.min_question_length:
            score -= 0.3
        elif length < 40:
            score -= 0.1
        elif length > self.max_question_length:
            score -= 0.2
        
        # Must end with question mark
        if not text.strip().endswith('?'):
            score -= 0.1
        
        # Check for proper capitalization
        if not text[0].isupper():
            score -= 0.1
        
        # Avoid overly short words (might be incomplete)
        words = text.split()
        if len(words) < 5:
            score -= 0.2
        
        # Check for proper Indonesian
        # Avoid questions that are just "Apa?", "Siapa?", etc.
        if len(words) <= 2:
            score -= 0.3
        
        return max(0.0, score)
    
    def _score_options(self, options: Dict) -> float:
        """Score options quality (0-1)"""
        score = 1.0
        
        if not options or len(options) != 5:
            return 0.0
        
        option_texts = list(options.values())
        lengths = [len(str(opt)) for opt in option_texts]
        
        # Check minimum length
        if any(length < self.min_option_length for length in lengths):
            score -= 0.2
        
        # Check maximum length
        if any(length > self.max_option_length for length in lengths):
            score -= 0.1
        
        # Check for balanced lengths (no one option much longer)
        avg_length = sum(lengths) / len(lengths)
        max_length = max(lengths)
        if max_length > avg_length * 2.5:
            score -= 0.2  # One option suspiciously longer
        
        # Check for duplicates
        if len(set(opt.lower().strip() for opt in option_texts)) != 5:
            score -= 0.3  # Duplicate options
        
        # Check for generic answers like "Semua benar", "Tidak ada yang benar"
        generic_answers = ['semua benar', 'tidak ada yang benar', 'a dan b', 'semua salah']
        for opt in option_texts:
            if any(generic in opt.lower() for generic in generic_answers):
                score -= 0.2
                break
        
        return max(0.0, score)
    
    def _score_explanation(self, explanation: str) -> float:
        """Score explanation quality (0-1)"""
        score = 1.0
        
        if not explanation:
            return 0.5  # Missing explanation is 50% penalty
        
        length = len(explanation)
        
        # Length checks
        if length < self.min_explanation_length:
            score -= 0.3
        elif length < 50:
            score -= 0.1
        elif length > 1000:
            score -= 0.1
        
        # Should explain WHY answer is correct
        quality_indicators = [
            'karena', 'sebab', 'oleh karena', 'hal ini', 
            'berdasarkan', 'sesuai dengan', 'menurut'
        ]
        if not any(indicator in explanation.lower() for indicator in quality_indicators):
            score -= 0.1
        
        return max(0.0, score)
    
    def _score_answer_distribution(self, correct_answer: str, options: Dict) -> float:
        """Check if correct answers are well distributed (not always A)"""
        # This will be tracked over batches
        # For single question, just ensure answer is valid
        return 1.0 if correct_answer in ['A', 'B', 'C', 'D', 'E'] else 0.0
    
    def _check_question_quality(self, question_data: Dict) -> List[str]:
        """Detailed question text checks"""
        issues = []
        text = question_data.get('question_text', '')
        
        # Must be a question
        if '?' not in text:
            issues.append("Question must contain '?'")
        
        # Check for vague questions
        vague_words = ['hal', 'sesuatu', 'ini itu']
        if any(word in text.lower() for word in vague_words):
            issues.append("Question seems vague or unclear")
        
        # Check for proper grammar indicators
        words = text.split()
        if len(words) < 5:
            issues.append("Question too short to be meaningful")
        
        return issues
    
    def _check_options_quality(self, question_data: Dict) -> List[str]:
        """Detailed options checks"""
        issues = []
        options = question_data.get('options', {})
        
        # Check each option
        for key, value in options.items():
            opt_text = str(value).strip()
            
            # Empty option
            if not opt_text:
                issues.append(f"Option {key} is empty")
            
            # Too short
            if len(opt_text) < 2:
                issues.append(f"Option {key} too short")
            
            # Should not start with special chars (except numbers)
            if opt_text and not opt_text[0].isalnum():
                issues.append(f"Option {key} starts with special character")
        
        return issues
    
    def _check_explanation_quality(self, question_data: Dict) -> List[str]:
        """Detailed explanation checks"""
        issues = []
        explanation = question_data.get('explanation', '')
        correct_answer = question_data.get('correct_answer', '')
        
        if not explanation:
            issues.append("Missing explanation (required for quality)")
            return issues
        
        # Should mention the correct answer
        if correct_answer and correct_answer not in explanation:
            issues.append("Explanation doesn't mention correct answer option")
        
        # Should not just repeat the answer
        if len(explanation) < 30:
            issues.append("Explanation too brief to be helpful")
        
        return issues
    
    def _check_answer_distribution(self, question_data: Dict) -> List[str]:
        """Check answer patterns"""
        issues = []
        correct_answer = question_data.get('correct_answer', '')
        
        # Just verify valid answer
        if correct_answer not in ['A', 'B', 'C', 'D', 'E']:
            issues.append(f"Invalid correct answer: {correct_answer}")
        
        return issues
    
    def batch_quality_check(
        self, 
        questions: List[Dict]
    ) -> Dict:
        """
        Check quality of entire batch
        Also checks batch-level patterns
        """
        results = {
            'total': len(questions),
            'high_quality': 0,
            'medium_quality': 0,
            'low_quality': 0,
            'rejected': 0,
            'questions': []
        }
        
        answer_distribution = {'A': 0, 'B': 0, 'C': 0, 'D': 0, 'E': 0}
        
        for q in questions:
            passes, score, issues = self.deep_quality_check(q)
            
            # Track answer distribution
            correct = q.get('correct_answer', '')
            if correct in answer_distribution:
                answer_distribution[correct] += 1
            
            # Categorize
            if score >= 0.85:
                results['high_quality'] += 1
                category = 'high'
            elif score >= 0.70:
                results['medium_quality'] += 1
                category = 'medium'
            elif score >= 0.50:
                results['low_quality'] += 1
                category = 'low'
            else:
                results['rejected'] += 1
                category = 'rejected'
            
            results['questions'].append({
                'question_id': q.get('content_hash', '')[:8],
                'question_text': q.get('question_text', '')[:50] + '...',
                'quality_score': score,
                'category': category,
                'passes': passes,
                'issues': issues
            })
        
        # Check answer distribution
        results['answer_distribution'] = answer_distribution
        
        # Warn if answers are not distributed
        total_answers = sum(answer_distribution.values())
        if total_answers > 0:
            for answer, count in answer_distribution.items():
                ratio = count / total_answers
                if ratio > 0.4:  # More than 40% same answer
                    results['warnings'] = results.get('warnings', [])
                    results['warnings'].append(
                        f"Answer '{answer}' appears in {ratio:.0%} of questions (may indicate bias)"
                    )
        
        return results


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    print("\n🧪 Testing Quality Controller\n")
    
    controller = QualityController(min_quality_score=0.7)
    
    # Test high-quality question
    high_quality = {
        'question_text': 'Berdasarkan Pancasila, sila pertama yang mengandung nilai ketuhanan adalah?',
        'options': {
            'A': 'Ketuhanan Yang Maha Esa',
            'B': 'Kemanusiaan yang Adil dan Beradab',
            'C': 'Persatuan Indonesia',
            'D': 'Kerakyatan yang Dipimpin oleh Hikmat',
            'E': 'Keadilan Sosial bagi Seluruh Rakyat'
        },
        'correct_answer': 'A',
        'explanation': 'Sila pertama Pancasila adalah "Ketuhanan Yang Maha Esa" yang menempatkan nilai ketuhanan sebagai dasar kehidupan berbangsa dan bernegara. Hal ini sesuai dengan pembukaan UUD 1945.',
        'test_category': 'cpns',
        'subject': 'wawasan_kebangsaan',
        'difficulty': 'mudah'
    }
    
    # Test low-quality question
    low_quality = {
        'question_text': 'Apa?',
        'options': {
            'A': 'Ya',
            'B': 'Ya',
            'C': 'Tidak',
            'D': 'Mungkin',
            'E': 'Semua benar'
        },
        'correct_answer': 'A',
        'explanation': 'Ya.',
        'test_category': 'cpns',
        'subject': 'tiu',
        'difficulty': 'mudah'
    }
    
    print("1️⃣  Testing HIGH-QUALITY question...")
    passes, score, issues = controller.deep_quality_check(high_quality)
    print(f"   Quality Score: {score:.2f}")
    print(f"   Passes: {'✅ YES' if passes else '❌ NO'}")
    if issues:
        print(f"   Issues: {len(issues)}")
        for issue in issues[:3]:
            print(f"     - {issue}")
    
    print("\n2️⃣  Testing LOW-QUALITY question...")
    passes, score, issues = controller.deep_quality_check(low_quality)
    print(f"   Quality Score: {score:.2f}")
    print(f"   Passes: {'✅ YES' if passes else '❌ NO'}")
    if issues:
        print(f"   Issues: {len(issues)}")
        for issue in issues:
            print(f"     - {issue}")
    
    print("\n3️⃣  Testing batch quality check...")
    batch = [high_quality, low_quality, high_quality]
    results = controller.batch_quality_check(batch)
    print(f"   Total: {results['total']}")
    print(f"   ✅ High Quality: {results['high_quality']}")
    print(f"   ⚠️  Medium Quality: {results['medium_quality']}")
    print(f"   ❌ Low Quality: {results['low_quality']}")
    print(f"   🚫 Rejected: {results['rejected']}")
    
    print("\n✅ Quality Controller tests complete!\n")