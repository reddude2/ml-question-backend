"""
Quality Control Configuration
Adjust these settings to control strictness
"""

# ============================================================================
# QUALITY THRESHOLDS
# ============================================================================

# Minimum quality score to accept question (0.0 to 1.0)
# 0.9 = Very strict (only excellent questions)
# 0.7 = Balanced (good questions)
# 0.5 = Lenient (acceptable questions)
MIN_QUALITY_SCORE = 0.75  # Recommended: 0.75 for high quality

# Minimum quality score for auto-approval (no manual review needed)
AUTO_APPROVE_THRESHOLD = 0.90

# ============================================================================
# LENGTH REQUIREMENTS
# ============================================================================

MIN_QUESTION_LENGTH = 30  # characters
MAX_QUESTION_LENGTH = 400

MIN_OPTION_LENGTH = 3
MAX_OPTION_LENGTH = 150

MIN_EXPLANATION_LENGTH = 40
MAX_EXPLANATION_LENGTH = 1000

# ============================================================================
# BATCH GENERATION SETTINGS
# ============================================================================

# Generate extra questions, then filter by quality
# If you want 10 questions, generate 15 and pick best 10
GENERATION_OVERPRODUCTION_RATIO = 1.5

# Maximum attempts to generate quality questions
MAX_GENERATION_ATTEMPTS = 3

# ============================================================================
# AI GENERATION SETTINGS (For High Quality)
# ============================================================================

# Temperature: Lower = more focused/conservative
# 0.3 = Very focused (recommended for exams)
# 0.7 = Balanced
# 1.0 = More creative
GENERATION_TEMPERATURE = 0.4  # Lower for exam questions

# Max tokens for response
MAX_TOKENS = 4096

# ============================================================================
# MANUAL REVIEW SETTINGS
# ============================================================================

# Require manual review if score below this threshold
MANUAL_REVIEW_THRESHOLD = 0.80

# Automatically reject if score below this
AUTO_REJECT_THRESHOLD = 0.50

# ============================================================================
# USER FEEDBACK QUALITY TRACKING
# ============================================================================

# Minimum usage before considering feedback
MIN_USAGE_FOR_FEEDBACK = 10

# Auto-retire question if correct_rate below this (after min usage)
MIN_ACCEPTABLE_CORRECT_RATE = 0.30  # 30%

# Auto-retire if correct_rate too high (too easy)
MAX_ACCEPTABLE_CORRECT_RATE = 0.95  # 95%

# ============================================================================
# ANSWER DISTRIBUTION (Prevent Bias)
# ============================================================================

# Warn if one answer option exceeds this ratio in batch
MAX_ANSWER_RATIO = 0.35  # 35% max for any single answer

# Ideal distribution per answer (20% each for A-E)
IDEAL_ANSWER_DISTRIBUTION = 0.20