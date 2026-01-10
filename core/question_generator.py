"""
Question Generator
Generate HIGH-QUALITY questions from materials using Gemini AI
"""

import json
import hashlib
import sys
import os
from typing import List, Dict, Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import google.generativeai as genai
from config import GEMINI_API_KEY, ML_MODEL, ML_TEMPERATURE, ML_MAX_TOKENS

class QuestionGenerator:
    """
    Generate HIGH-QUALITY questions from learning materials using Gemini AI
    Focus: Quality over Quantity
    """
    
    def __init__(self, api_key: str = GEMINI_API_KEY):
        if not api_key:
            raise ValueError("Gemini API key is required")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(ML_MODEL)
        # Lower temperature for more focused, consistent output
        self.temperature = 0.4  # Lower = more focused (better for exams)
        self.max_tokens = ML_MAX_TOKENS
    
    def generate_from_material(
        self,
        material_text: str,
        test_category: str,
        subject: str,
        difficulty: str = "sedang",
        count: int = 10,
        subtype: Optional[str] = None
    ) -> List[Dict]:
        """
        Generate questions from material text
        
        Args:
            material_text: Source material text
            test_category: polri or cpns
            subject: Subject area
            difficulty: mudah, sedang, or sulit
            count: Number of questions to generate
            subtype: Optional subtype (for TIU: verbal, numerik, figural)
            
        Returns:
            List of generated questions
        """
        # Validate inputs
        if not material_text or len(material_text) < 100:
            raise ValueError("Material text too short (minimum 100 characters)")
        
        if count < 1 or count > 50:
            raise ValueError("Count must be between 1 and 50")
        
        # Build prompt
        prompt = self._build_prompt(
            material_text,
            test_category,
            subject,
            difficulty,
            count,
            subtype
        )
        
        # Generate with retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.model.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=self.temperature,
                        max_output_tokens=self.max_tokens,
                    )
                )
                
                # Parse response
                questions = self._parse_response(response.text)
                
                # Add metadata and hash to each question
                for q in questions:
                    q['test_category'] = test_category
                    q['subject'] = subject
                    q['difficulty'] = difficulty
                    if subtype:
                        q['subtype'] = subtype
                    
                    # Generate content hash
                    q['content_hash'] = self._generate_hash(
                        q['question_text'],
                        q['correct_answer']
                    )
                
                return questions[:count]  # Return exactly count questions
                
            except Exception as e:
                if attempt == max_retries - 1:
                    raise Exception(f"Failed to generate questions after {max_retries} attempts: {e}")
                continue
        
        return []
    
    def generate_with_quality_control(
        self,
        material_text: str,
        test_category: str,
        subject: str,
        difficulty: str = "sedang",
        target_count: int = 10,
        min_quality_score: float = 0.75,
        max_attempts: int = 3,
        subtype: Optional[str] = None
    ) -> Dict:
        """
        Generate questions with QUALITY CONTROL
        Will retry if quality is insufficient
        
        Args:
            material_text: Source material
            test_category: polri or cpns
            subject: Subject area
            difficulty: mudah, sedang, or sulit
            target_count: Desired number of quality questions
            min_quality_score: Minimum acceptable quality score
            max_attempts: Maximum generation attempts
            subtype: Optional subtype
            
        Returns:
            Dict with generated questions and quality stats
        """
        try:
            from core.quality_controller import QualityController
        except ImportError:
            # Fallback if quality_controller not available
            questions = self.generate_from_material(
                material_text, test_category, subject, 
                difficulty, target_count, subtype
            )
            return {
                'generated_count': len(questions),
                'target_count': target_count,
                'selected_count': len(questions),
                'questions': questions,
                'attempts': 1,
                'avg_quality_score': 0.0
            }
        
        controller = QualityController(min_quality_score=min_quality_score)
        
        # Generate extra questions (overproduction for quality filtering)
        generate_count = int(target_count * 1.5)  # Generate 50% more
        
        all_questions = []
        
        for attempt in range(max_attempts):
            try:
                # Generate batch
                questions = self.generate_from_material(
                    material_text,
                    test_category,
                    subject,
                    difficulty,
                    generate_count,
                    subtype
                )
                
                # Quality check
                quality_results = controller.batch_quality_check(questions)
                
                # Filter high and medium quality
                for q_data in quality_results['questions']:
                    if q_data['category'] in ['high', 'medium']:
                        # Find original question
                        for q in questions:
                            if q.get('content_hash', '')[:8] == q_data['question_id']:
                                q['quality_score'] = q_data['quality_score']
                                q['quality_category'] = q_data['category']
                                all_questions.append(q)
                                break
                
                # Check if we have enough quality questions
                if len(all_questions) >= target_count:
                    break
                    
            except Exception as e:
                if attempt == max_attempts - 1:
                    # If all attempts failed, return what we have
                    break
                continue
        
        # Sort by quality score and take top N
        all_questions.sort(key=lambda x: x.get('quality_score', 0), reverse=True)
        selected_questions = all_questions[:target_count]
        
        return {
            'generated_count': len(all_questions),
            'target_count': target_count,
            'selected_count': len(selected_questions),
            'avg_quality_score': sum(q.get('quality_score', 0) for q in selected_questions) / len(selected_questions) if selected_questions else 0,
            'questions': selected_questions,
            'attempts': attempt + 1
        }
    
    def _build_prompt(
        self,
        material_text: str,
        test_category: str,
        subject: str,
        difficulty: str,
        count: int,
        subtype: Optional[str] = None
    ) -> str:
        """Build QUALITY-FOCUSED prompt for Gemini"""
        
        # Truncate material if too long
        if len(material_text) > 4000:
            material_text = material_text[:4000] + "\n...(material continues)"
        
        # Build subject description
        subject_desc = self._get_subject_description(test_category, subject, subtype)
        
        # Difficulty-specific instructions
        difficulty_guides = {
            'mudah': """
DIFFICULTY: MUDAH (Easy)
- Questions should test direct recall and basic understanding
- Information should be EXPLICITLY stated in material
- Options should be clearly distinguishable
- Avoid tricky wording or complex logic
- Answer should be obvious to someone who read the material
            """,
            'sedang': """
DIFFICULTY: SEDANG (Medium)
- Questions should require understanding and basic inference
- May require connecting multiple concepts from material
- Options should include plausible distractors
- Require analytical thinking
- Answer should be clear after careful thought
            """,
            'sulit': """
DIFFICULTY: SULIT (Hard)
- Questions should require deep analysis and critical thinking
- May require synthesis of multiple concepts
- Options should be subtle and require careful evaluation
- Test higher-order thinking skills
- Answer requires expert understanding
            """
        }
        
        prompt = f"""You are an EXPERT Indonesian civil service exam question creator with 15+ years of experience.

⚠️ CRITICAL: QUALITY IS PRIORITY #1 ⚠️

QUALITY REQUIREMENTS (NON-NEGOTIABLE):
✓ Questions must be CRYSTAL CLEAR and UNAMBIGUOUS
✓ Base questions ONLY on provided material (no external knowledge)
✓ Each question tests ONE specific concept
✓ All 5 options must be relevant and plausible
✓ Only ONE answer is definitively correct
✓ Explanations must reference material and explain WHY
✓ Use proper Indonesian grammar (formal, professional)
✓ NO trick questions or intentionally confusing wording
✓ NO generic answers like "Semua benar" or "Tidak ada yang benar"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

MATERIAL TO ANALYZE:
{material_text}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SPECIFICATIONS:
- Test Category: {test_category.upper()}
- Subject: {subject_desc}
{"• Subtype: " + subtype if subtype else ""}
- Difficulty Level: {difficulty}
- Questions Needed: {count}
- Language: Bahasa Indonesia (Formal)

{difficulty_guides.get(difficulty, '')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

QUALITY CHECKLIST (Verify EACH question):
□ Question is specific and clear (not vague)
□ Question ends with proper question mark (?)
□ All 5 options (A-E) are relevant and realistic
□ Options are similar in length (20-80 characters each)
□ NO duplicate or near-duplicate options
□ Correct answer is definitively correct based on material
□ Wrong answers are plausible but clearly incorrect
□ Explanation clearly states WHY answer is correct
□ Explanation references specific parts of material
□ Options do NOT give away the answer (balanced length)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

OUTPUT FORMAT (Pure JSON only, no markdown):
[
  {{
    "question_text": "Berdasarkan materi, [specific question about material]?",
    "options": {{
      "A": "First realistic option (30-70 chars)",
      "B": "Second realistic option (30-70 chars)",
      "C": "Third realistic option (30-70 chars)",
      "D": "Fourth realistic option (30-70 chars)",
      "E": "Fifth realistic option (30-70 chars)"
    }},
    "correct_answer": "A",
    "explanation": "Jawaban yang benar adalah A karena berdasarkan materi, [specific reference to material]. Pilihan B salah karena [brief reason]. Pilihan C, D, dan E juga tidak tepat karena [brief reason]."
  }}
]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ANSWER DISTRIBUTION:
- Distribute correct answers across A, B, C, D, E
- DON'T make all answers "A"
- Mix it up naturally

OPTION QUALITY:
- Each option should be 20-80 characters
- Keep similar lengths (don't make correct answer much longer)
- Make all options grammatically similar
- Use parallel structure

EXPLANATION QUALITY:
- Minimum 50 characters
- State WHY answer is correct
- Reference specific material
- Briefly explain why others are wrong

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Generate {count} EXCELLENT QUALITY questions now:"""
        
        return prompt
    
    def _get_subject_description(self, test_category: str, subject: str, subtype: Optional[str]) -> str:
        """Get subject description for prompt"""
        descriptions = {
            'polri': {
                'bahasa_inggris': 'English Language',
                'numerik': 'Numerical Reasoning',
                'pengetahuan_umum': 'General Knowledge',
                'wawasan_kebangsaan': 'National Insight'
            },
            'cpns': {
                'tiu': 'General Intelligence Test',
                'wawasan_kebangsaan': 'National Insight',
                'tkp': 'Personal Characteristics Test'
            }
        }
        
        desc = descriptions.get(test_category, {}).get(subject, subject)
        if subtype:
            desc += f" - {subtype.title()}"
        
        return desc
    
    def _parse_response(self, response_text: str) -> List[Dict]:
        """Parse Gemini response to extract questions"""
        try:
            # Remove markdown code blocks if present
            text = response_text.strip()
            
            # Remove various markdown formats
            if text.startswith('```json'):
                text = text[7:]
            elif text.startswith('```'):
                text = text[3:]
            
            if text.endswith('```'):
                text = text[:-3]
            
            text = text.strip()
            
            # Parse JSON
            questions = json.loads(text)
            
            # Validate structure
            if not isinstance(questions, list):
                raise ValueError("Response is not a list")
            
            validated_questions = []
            for q in questions:
                if self._validate_question_structure(q):
                    validated_questions.append(q)
            
            return validated_questions
            
        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse JSON response: {e}\nResponse: {response_text[:200]}")
        except Exception as e:
            raise Exception(f"Failed to parse response: {e}")
    
    def _validate_question_structure(self, question: Dict) -> bool:
        """Validate question has required fields"""
        required_fields = ['question_text', 'options', 'correct_answer']
        
        # Check required fields
        for field in required_fields:
            if field not in question:
                return False
        
        # Check options
        options = question.get('options', {})
        if not isinstance(options, dict):
            return False
        
        required_options = ['A', 'B', 'C', 'D', 'E']
        for opt in required_options:
            if opt not in options:
                return False
            # Check option is not empty
            if not str(options[opt]).strip():
                return False
        
        # Check correct answer
        correct = question.get('correct_answer', '')
        if correct not in required_options:
            return False
        
        return True
    
    def _generate_hash(self, question_text: str, correct_answer: str) -> str:
        """Generate content hash for duplicate detection"""
        content = f"{question_text}|{correct_answer}"
        return hashlib.sha256(content.encode()).hexdigest()


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def generate_questions_from_material(
    material_text: str,
    test_category: str,
    subject: str,
    difficulty: str = "sedang",
    count: int = 10
) -> List[Dict]:
    """
    Convenience function to generate questions
    
    Args:
        material_text: Source material
        test_category: polri or cpns
        subject: Subject area
        difficulty: mudah, sedang, or sulit
        count: Number of questions
        
    Returns:
        List of generated questions
    """
    generator = QuestionGenerator()
    return generator.generate_from_material(
        material_text,
        test_category,
        subject,
        difficulty,
        count
    )


def generate_quality_questions(
    material_text: str,
    test_category: str,
    subject: str,
    difficulty: str = "sedang",
    count: int = 10,
    min_quality: float = 0.75
) -> Dict:
    """
    Generate questions with quality control
    
    Args:
        material_text: Source material
        test_category: polri or cpns
        subject: Subject area
        difficulty: mudah, sedang, or sulit
        count: Number of quality questions desired
        min_quality: Minimum quality score (0.0-1.0)
        
    Returns:
        Dict with questions and quality stats
    """
    generator = QuestionGenerator()
    return generator.generate_with_quality_control(
        material_text,
        test_category,
        subject,
        difficulty,
        count,
        min_quality
    )


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    print("\n🧪 Testing ENHANCED Question Generator\n")
    
    # Test material
    test_material = """
    Pancasila adalah dasar negara Indonesia yang terdiri dari lima sila.
    Sila pertama adalah Ketuhanan Yang Maha Esa yang menekankan nilai-nilai ketuhanan dalam kehidupan berbangsa.
    Sila kedua adalah Kemanusiaan yang Adil dan Beradab yang mengajarkan penghormatan terhadap martabat manusia.
    Sila ketiga adalah Persatuan Indonesia yang mendorong kesatuan di tengah keberagaman suku, agama, dan budaya.
    Sila keempat adalah Kerakyatan yang Dipimpin oleh Hikmat Kebijaksanaan dalam Permusyawaratan/Perwakilan yang menekankan demokrasi musyawarah.
    Sila kelima adalah Keadilan Sosial bagi Seluruh Rakyat Indonesia yang mengutamakan pemerataan kesejahteraan.
    Pancasila pertama kali dirumuskan oleh Ir. Soekarno pada tanggal 1 Juni 1945 dalam sidang BPUPKI.
    """
    
    try:
        print("=" * 60)
        print("TEST 1: Basic Generation")
        print("=" * 60 + "\n")
        
        generator = QuestionGenerator()
        questions = generator.generate_from_material(
            material_text=test_material,
            test_category="cpns",
            subject="wawasan_kebangsaan",
            difficulty="mudah",
            count=3
        )
        
        print(f"✅ Generated {len(questions)} questions\n")
        
        for i, q in enumerate(questions, 1):
            print(f"Question {i}:")
            print(f"  Text: {q['question_text'][:70]}...")
            print(f"  Options: {list(q['options'].keys())}")
            print(f"  Correct: {q['correct_answer']}")
            print(f"  Has explanation: {'✅' if q.get('explanation') else '❌'}")
            print(f"  Hash: {q['content_hash'][:16]}...")
            print()
        
        # Test with quality control
        print("=" * 60)
        print("TEST 2: Quality-Controlled Generation")
        print("=" * 60 + "\n")
        
        result = generator.generate_with_quality_control(
            material_text=test_material,
            test_category="cpns",
            subject="wawasan_kebangsaan",
            difficulty="sedang",
            target_count=3,
            min_quality_score=0.70
        )
        
        print(f"✅ Quality generation complete!")
        print(f"   Generated: {result['generated_count']}")
        print(f"   Selected: {result['selected_count']}")
        print(f"   Avg Quality: {result['avg_quality_score']:.2f}")
        print(f"   Attempts: {result['attempts']}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()