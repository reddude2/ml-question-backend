"""
Material Quality Checker
Ensure source materials are high-quality before generation
"""

import sys
import os
from typing import Dict, List, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class MaterialQualityChecker:
    """
    Check if uploaded material is suitable for question generation
    """
    
    def __init__(self):
        self.min_word_count = 50
        self.max_word_count = 20000
        self.min_unique_words = 30
        self.min_sentences = 5
    
    def check_material_quality(self, text: str) -> Tuple[bool, float, List[str]]:
        """
        Check material quality
        
        Args:
            text: Extracted material text
            
        Returns:
            Tuple of (is_acceptable, quality_score, issues)
        """
        issues = []
        score = 1.0
        
        # Basic checks
        if not text or len(text.strip()) < 100:
            return False, 0.0, ["Material too short (minimum 100 characters)"]
        
        # Word count check
        words = text.split()
        word_count = len(words)
        
        if word_count < self.min_word_count:
            issues.append(f"Too few words: {word_count} (minimum {self.min_word_count})")
            score -= 0.3
        
        if word_count > self.max_word_count:
            issues.append(f"Too many words: {word_count} (maximum {self.max_word_count})")
            score -= 0.1
        
        # Unique words (vocabulary richness)
        unique_words = len(set(word.lower() for word in words if len(word) > 3))
        if unique_words < self.min_unique_words:
            issues.append(f"Limited vocabulary: {unique_words} unique words")
            score -= 0.2
        
        # Sentence count
        sentences = [s.strip() for s in text.split('.') if s.strip()]
        sentence_count = len(sentences)
        
        if sentence_count < self.min_sentences:
            issues.append(f"Too few sentences: {sentence_count} (minimum {self.min_sentences})")
            score -= 0.2
        
        # Check for proper structure
        if not any(char in text for char in '.!?'):
            issues.append("No proper sentence endings (. ! ?)")
            score -= 0.2
        
        # Check for excessive repetition
        word_freq = {}
        for word in words:
            word_lower = word.lower()
            if len(word_lower) > 4:  # Only count meaningful words
                word_freq[word_lower] = word_freq.get(word_lower, 0) + 1
        
        if word_freq:
            max_freq = max(word_freq.values())
            if max_freq > word_count * 0.1:  # More than 10% repetition
                issues.append("Excessive word repetition detected")
                score -= 0.1
        
        # Check readability (average sentence length)
        if sentence_count > 0:
            avg_sentence_length = word_count / sentence_count
            if avg_sentence_length < 5:
                issues.append("Sentences too short (may be fragmented)")
                score -= 0.1
            elif avg_sentence_length > 50:
                issues.append("Sentences too long (may be hard to parse)")
                score -= 0.1
        
        # Calculate final score
        score = max(0.0, min(1.0, score))
        is_acceptable = score >= 0.6 and len(issues) < 3
        
        return is_acceptable, score, issues
    
    def get_material_stats(self, text: str) -> Dict:
        """Get detailed material statistics"""
        words = text.split()
        sentences = [s.strip() for s in text.split('.') if s.strip()]
        
        return {
            'total_chars': len(text),
            'total_words': len(words),
            'unique_words': len(set(word.lower() for word in words)),
            'total_sentences': len(sentences),
            'avg_sentence_length': len(words) / len(sentences) if sentences else 0,
            'avg_word_length': sum(len(word) for word in words) / len(words) if words else 0
        }


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    print("\n🧪 Testing Material Quality Checker\n")
    
    checker = MaterialQualityChecker()
    
    # Good material
    good_material = """
    Pancasila adalah dasar negara Indonesia yang terdiri dari lima sila.
    Sila pertama adalah Ketuhanan Yang Maha Esa, yang menekankan pentingnya nilai-nilai ketuhanan.
    Sila kedua adalah Kemanusiaan yang Adil dan Beradab, yang mengajarkan penghormatan terhadap sesama manusia.
    Sila ketiga adalah Persatuan Indonesia, yang mendorong persatuan di tengah keberagaman.
    Sila keempat adalah Kerakyatan yang Dipimpin oleh Hikmat Kebijaksanaan dalam Permusyawaratan/Perwakilan.
    Sila kelima adalah Keadilan Sosial bagi Seluruh Rakyat Indonesia, yang menekankan pemerataan kesejahteraan.
    Pancasila dirumuskan oleh para pendiri bangsa sebagai ideologi negara yang mencerminkan nilai-nilai luhur bangsa Indonesia.
    """
    
    # Poor material
    poor_material = "Pancasila. Lima sila. Indonesia. Penting."
    
    print("1️⃣  Testing GOOD material...")
    is_ok, score, issues = checker.check_material_quality(good_material)
    stats = checker.get_material_stats(good_material)
    print(f"   Quality Score: {score:.2f}")
    print(f"   Acceptable: {'✅ YES' if is_ok else '❌ NO'}")
    print(f"   Words: {stats['total_words']}")
    print(f"   Sentences: {stats['total_sentences']}")
    if issues:
        print(f"   Issues: {issues}")
    
    print("\n2️⃣  Testing POOR material...")
    is_ok, score, issues = checker.check_material_quality(poor_material)
    stats = checker.get_material_stats(poor_material)
    print(f"   Quality Score: {score:.2f}")
    print(f"   Acceptable: {'✅ YES' if is_ok else '❌ NO'}")
    print(f"   Issues:")
    for issue in issues:
        print(f"     - {issue}")
    
    print("\n✅ Material checker tests complete!\n")