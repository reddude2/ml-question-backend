"""
ML Configuration
Gemini API and ML settings
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ============================================================================
# GEMINI API CONFIGURATION
# ============================================================================

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
ML_PROVIDER = os.getenv("ML_PROVIDER", "gemini")
ML_MODEL = os.getenv("ML_MODEL", "gemini-1.5-flash")
ML_MAX_TOKENS = int(os.getenv("ML_MAX_TOKENS", "4096"))
ML_TEMPERATURE = float(os.getenv("ML_TEMPERATURE", "0.7"))

# Validate API key
if not GEMINI_API_KEY or GEMINI_API_KEY == "your-gemini-api-key-here":
    print("⚠️  WARNING: GEMINI_API_KEY not set in .env file!")
    print("   Get your key from: https://makersuite.google.com/app/apikey")

# ============================================================================
# UPLOAD CONFIGURATION
# ============================================================================

MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "10"))
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

ALLOWED_FILE_TYPES = os.getenv("ALLOWED_FILE_TYPES", "pdf,docx,txt").split(",")
UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "uploads/materials")

# Create upload folder if not exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ============================================================================
# ML GENERATION SETTINGS
# ============================================================================

# Question generation limits per request
MAX_QUESTIONS_PER_GENERATION = 50

# Prompt settings
GENERATION_PROMPTS = {
    "system": """You are an expert question generator for Indonesian civil service exams (POLRI & CPNS).
Your task is to create high-quality, accurate multiple choice questions based on provided materials.""",
    
    "user_template": """Generate {count} multiple choice questions based on this material.

MATERIAL:
{material_text}

REQUIREMENTS:
- Test Category: {test_category}
- Subject: {subject}
- Difficulty: {difficulty}
- Language: Indonesian
- Format: 5 options (A-E)
- Include explanation

RETURN JSON FORMAT:
[
  {{
    "question_text": "Question here?",
    "options": {{
      "A": "Option A",
      "B": "Option B",
      "C": "Option C",
      "D": "Option D",
      "E": "Option E"
    }},
    "correct_answer": "A",
    "explanation": "Explanation here"
  }}
]

Generate {count} questions now:"""
}

# ============================================================================
# VALIDATION SETTINGS
# ============================================================================

# Minimum text length for material (characters)
MIN_MATERIAL_LENGTH = 100

# Maximum text length for material (characters)
MAX_MATERIAL_LENGTH = 50000

# Similarity threshold for duplicate detection (0-1)
DUPLICATE_THRESHOLD = 0.85

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def validate_api_key() -> bool:
    """Check if API key is configured"""
    return bool(GEMINI_API_KEY and GEMINI_API_KEY != "your-gemini-api-key-here")

def get_allowed_file_size() -> str:
    """Get human-readable file size limit"""
    return f"{MAX_FILE_SIZE_MB} MB"

def is_file_type_allowed(filename: str) -> bool:
    """Check if file extension is allowed"""
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    return ext in ALLOWED_FILE_TYPES

def get_upload_path(filename: str) -> str:
    """Get full upload path for file"""
    return os.path.join(UPLOAD_FOLDER, filename)

# ============================================================================
# CONFIGURATION SUMMARY
# ============================================================================

def print_config():
    """Print ML configuration summary"""
    print("\n" + "=" * 60)
    print("ML CONFIGURATION")
    print("=" * 60)
    print(f"Provider: {ML_PROVIDER}")
    print(f"Model: {ML_MODEL}")
    print(f"API Key: {'✅ Configured' if validate_api_key() else '❌ Not Set'}")
    print(f"Max Tokens: {ML_MAX_TOKENS}")
    print(f"Temperature: {ML_TEMPERATURE}")
    print(f"Upload Folder: {UPLOAD_FOLDER}")
    print(f"Max File Size: {get_allowed_file_size()}")
    print(f"Allowed Types: {', '.join(ALLOWED_FILE_TYPES)}")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    print_config()