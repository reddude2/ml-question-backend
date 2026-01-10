"""
System Configuration
Test types, tier limits, and system constants
"""

import os
from dotenv import load_dotenv

# Load environment variables FIRST
load_dotenv()

# ============================================================================
# TEST STRUCTURE
# ============================================================================

TES_POLRI = {
    "bahasa_inggris": {
        "label": "Bahasa Inggris",
        "count": 60,
        "time": 60
    },
    "numerik": {
        "label": "Numerik",
        "count": 20,
        "time": 30
    },
    "pengetahuan_umum": {
        "label": "Pengetahuan Umum",
        "count": 30,
        "time": 40
    },
    "wawasan_kebangsaan": {
        "label": "Wawasan Kebangsaan",
        "count": 40,
        "time": 50
    }
}

TES_CPNS = {
    "tiu": {
        "label": "Tes Intelegensi Umum",
        "subtypes": ["verbal", "numerik", "figural"],
        "count": 30,
        "time": 40
    },
    "wawasan_kebangsaan": {
        "label": "Wawasan Kebangsaan",
        "count": 30,
        "time": 35
    },
    "tkp": {
        "label": "Tes Karakteristik Pribadi",
        "count": 35,
        "time": 40
    }
}

# ============================================================================
# TIER LIMITS
# ============================================================================

TIER_LIMITS = {
    "free": {
        "max_questions_per_session": 20,
        "max_sessions_per_day": 3,
        "explanation": False,
        "simulation": False
    },
    "basic": {
        "max_questions_per_session": 50,
        "max_sessions_per_day": 10,
        "explanation": True,
        "simulation": False
    },
    "premium": {
        "max_questions_per_session": 250,
        "max_sessions_per_day": "unlimited",
        "explanation": True,
        "simulation": True
    }
}

# ============================================================================
# UI LABELS (Indonesian)
# ============================================================================

TIER_LABELS = {
    "free": "Gratis",
    "basic": "Basic",
    "premium": "Premium"
}

TEST_TYPE_LABELS = {
    "polri": "POLRI",
    "cpns": "CPNS",
    "campur": "Campur (POLRI & CPNS)"
}

DIFFICULTY_LABELS = {
    "mudah": "Mudah",
    "sedang": "Sedang",
    "sulit": "Sulit"
}

# ============================================================================
# ML CONFIGURATION
# ============================================================================

# Gemini API Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
ML_PROVIDER = os.getenv("ML_PROVIDER", "gemini")
ML_MODEL = os.getenv("ML_MODEL", "gemini-2.5-flash")  # ← UPDATED
ML_MAX_TOKENS = int(os.getenv("ML_MAX_TOKENS", "4096"))
ML_TEMPERATURE = float(os.getenv("ML_TEMPERATURE", "0.7"))

# Upload Configuration
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "10"))
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
ALLOWED_FILE_TYPES = os.getenv("ALLOWED_FILE_TYPES", "pdf,docx,txt").split(",")
UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "uploads/materials")

# Create upload folder if not exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ML Generation Settings
MAX_QUESTIONS_PER_GENERATION = 50

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def validate_api_key() -> bool:
    """Check if API key is configured"""
    return bool(GEMINI_API_KEY and GEMINI_API_KEY != "your-gemini-api-key-here")  # ← FIXED

def is_file_type_allowed(filename: str) -> bool:
    """Check if file extension is allowed"""
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    return ext in ALLOWED_FILE_TYPES

def get_upload_path(filename: str) -> str:
    """Get full upload path for file"""
    return os.path.join(UPLOAD_FOLDER, filename)

# ============================================================================
# VALIDATION
# ============================================================================

# Warn if API key not configured
if not validate_api_key():
    print("⚠️  WARNING: GEMINI_API_KEY not configured in .env")
    print("   Get your key from: https://makersuite.google.com/app/apikey")