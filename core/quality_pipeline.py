"""
Complete Quality Control Pipeline
Orchestrates all quality control components
"""

import sys
import os
from typing import Dict, List, Optional  # ← ADD Optional here

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.material_quality_checker import MaterialQualityChecker
from core.material_processor import MaterialProcessor
from core.question_generator import QuestionGenerator
from core.quality_controller import QualityController
from core.question_validator import QuestionValidator

class QualityPipeline:
    """
    End-to-end quality pipeline:
    Material Check → Process → Generate → Validate → Filter
    """
    
    def __init__(
        self,
        min_material_quality: float = 0.6,
        min_question_quality: float = 0.75,
        target_quality_score: float = 0.85
    ):
        self.material_checker = MaterialQualityChecker()
        self.material_processor = MaterialProcessor()
        self.generator = QuestionGenerator()
        self.quality_controller = QualityController(min_quality_score=min_question_quality)
        self.validator = QuestionValidator()
        
        self.min_material_quality = min_material_quality
        self.min_question_quality = min_question_quality
        self.target_quality_score = target_quality_score
    
    def process_and_generate(
        self,
        file_path: str,
        test_category: str,
        subject: str,
        difficulty: str,
        count: int,
        subtype: Optional[str] = None
    ) -> Dict:
        """
        Complete pipeline from file to quality questions
        
        Returns:
            Dict with results and quality report
        """
        result = {
            'success': False,
            'stage': 'initialization',
            'material_quality': {},
            'generation_quality': {},
            'questions': [],
            'stats': {}
        }
        
        try:
            # Stage 1: Process material
            result['stage'] = 'processing_material'
            processed = self.material_processor.process_file(file_path)
            extracted_text = processed['extracted_text']
            
            # Stage 2: Check material quality
            result['stage'] = 'checking_material_quality'
            is_acceptable, mat_score, mat_issues = self.material_checker.check_material_quality(extracted_text)
            
            result['material_quality'] = {
                'score': mat_score,
                'acceptable': is_acceptable,
                'issues': mat_issues,
                'stats': self.material_checker.get_material_stats(extracted_text)
            }
            
            if not is_acceptable:
                result['error'] = f"Material quality insufficient: {mat_score:.2f}"
                return result
            
            # Stage 3: Generate questions with quality control
            result['stage'] = 'generating_questions'
            generation_result = self.generator.generate_with_quality_control(
                material_text=extracted_text,
                test_category=test_category,
                subject=subject,
                difficulty=difficulty,
                target_count=count,
                min_quality_score=self.min_question_quality,
                max_attempts=3,
                subtype=subtype
            )
            
            # Stage 4: Deep quality check
            result['stage'] = 'quality_checking'
            quality_results = self.quality_controller.batch_quality_check(
                generation_result['questions']
            )
            
            # Stage 5: Filter by target quality score
            result['stage'] = 'filtering'
            high_quality_questions = [
                q for q in generation_result['questions']
                if q.get('quality_score', 0) >= self.target_quality_score
            ]
            
            # If not enough high-quality, include medium
            if len(high_quality_questions) < count:
                medium_quality = [
                    q for q in generation_result['questions']
                    if self.min_question_quality <= q.get('quality_score', 0) < self.target_quality_score
                ]
                high_quality_questions.extend(medium_quality)
            
            # Take top N by score
            high_quality_questions.sort(
                key=lambda x: x.get('quality_score', 0),
                reverse=True
            )
            final_questions = high_quality_questions[:count]
            
            # Results
            result['success'] = True
            result['stage'] = 'complete'
            result['questions'] = final_questions
            result['generation_quality'] = quality_results
            result['stats'] = {
                'material_score': mat_score,
                'requested_count': count,
                'generated_count': generation_result['generated_count'],
                'high_quality_count': len([q for q in generation_result['questions'] if q.get('quality_score', 0) >= self.target_quality_score]),
                'delivered_count': len(final_questions),
                'avg_quality_score': sum(q.get('quality_score', 0) for q in final_questions) / len(final_questions) if final_questions else 0,
                'generation_attempts': generation_result.get('attempts', 1)
            }
            
            return result
            
        except Exception as e:
            result['error'] = str(e)
            return result


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    print("\n🧪 Testing Quality Pipeline\n")
    
    # This would need an actual file to test
    print("Quality Pipeline ready for integration!")
    print("\nUsage example:")
    print("""
    pipeline = QualityPipeline(
        min_material_quality=0.6,
        min_question_quality=0.75,
        target_quality_score=0.85
    )
    
    result = pipeline.process_and_generate(
        file_path='uploads/materials/materi.pdf',
        test_category='cpns',
        subject='tiu',
        difficulty='mudah',
        count=10
    )
    
    if result['success']:
        print(f"Generated {len(result['questions'])} quality questions")
        print(f"Average quality: {result['stats']['avg_quality_score']:.2f}")
    """)
    
    print("\n✅ Pipeline ready!\n")