"""
FastAPI Application
ML Question System - Backend API with NEVER REPEAT System
Version 3.1 - With Exam Mode, Tiers & 4 Roles + Materials Management
"""

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import routers
from routers import auth, users, questions, sessions, progress, admin, review
from routers import exam  # Exam mode router
from routers import materials  # Materials management router
from middleware.auth import verify_jwt_middleware

# ============================================================================
# APP CONFIGURATION
# ============================================================================

app = FastAPI(
    title="ML Question System API",
    description="""
    Backend API untuk sistem soal ujian POLRI & CPNS dengan Machine Learning dan NEVER REPEAT System.
    
    ## 🎯 Core Features
    
    * **Authentication** - JWT-based authentication with double-layer security
    * **User Management** - Role & tier-based access control
    * **Question Bank** - POLRI & CPNS questions with smart filtering
    * **Materials Management** - Input & manage learning materials for ML question generation
    * **NEVER REPEAT Sessions** - Users never see same question twice (forever)
    * **Review Mode** - Practice past sessions anytime
    * **Progress Tracking** - Lifetime statistics and analytics
    * **Session Management** - Complete session lifecycle with timing
    * **Admin Dashboard** - User and question management
    
    ## 🔥 New in v3.1 - MATERIALS MANAGEMENT
    
    ### 📚 Materials Management (NEW)
    * **Material Input** - Add learning materials for question generation
    * **ML Question Generation** - Generate questions from materials using Gemini AI
    * **Quality Control** - Validate and manage generated questions
    * **Content Organization** - Tag and categorize materials by subject
    
    ### 🎓 Exam Mode (Premium Only)
    * **Mixed Subject Exams** - Real exam simulation
    * **CPNS Exam**: 50 TIU + 50 TWK + 50 TKP = 150 questions (120 min)
    * **POLRI Exam**: 50 B.Inggris + 50 TIU + 50 TWK + 50 Numerik = 200 questions (150 min)
    * **Time Limits** - Enforced time limits
    * **Never Repeat** - Still applies in exam mode
    
    ### 💎 Tier System (3 Tiers)
    * **FREE**: Practice mode only, max 10 questions, no explanations
    * **BASIC**: Practice + Review, max 50 questions, has explanations
    * **PREMIUM**: Full access (Exam mode + all features), max 200 questions
    
    ### 👥 Role System (4 Roles)
    * **admin**: Full access + user management + materials management
    * **user_cpns**: CPNS questions only
    * **user_polri**: POLRI questions only
    * **user_mixed**: Both CPNS & POLRI access
    
    ## 🔒 Security Layers
    
    * **Layer 1**: Global middleware for all requests
    * **Layer 2**: Per-endpoint dependencies with role checking
    * **Layer 3**: Tier-based feature access control
    
    ## 📚 Test Categories
    
    ### POLRI
    * Bahasa Inggris
    * Numerik (Penalaran Numerik)
    * TIU (Tes Intelegensi Umum)
    * TWK (Tes Wawasan Kebangsaan)
    
    ### CPNS
    * TIU (Tes Intelegensi Umum)
    * TWK (Tes Wawasan Kebangsaan)
    * TKP (Tes Karakteristik Pribadi)
    """,
    version="3.1.0",
    contact={
        "name": "ML Question System",
        "email": "support@mlquestion.com"
    },
    license_info={
        "name": "Proprietary",
    }
)

# ============================================================================
# CORS CONFIGURATION - WITH file:// SUPPORT
# ============================================================================

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")

# Prepare allowed origins list
# Add "null" origin to support file:// protocol (for local HTML files)
if "*" in ALLOWED_ORIGINS:
    # Allow all origins including file://
    cors_origins = ["*"]
else:
    # Add specific origins + null for file://
    cors_origins = ALLOWED_ORIGINS + ["null"]

print(f"🌐 CORS Allowed Origins: {cors_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)

# ============================================================================
# SECURITY MIDDLEWARE
# ============================================================================

# Global JWT verification middleware
app.middleware("http")(verify_jwt_middleware)

# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Handle 404 Not Found errors"""
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "status": "error",
            "message": "Endpoint tidak ditemukan",
            "detail": f"Path '{request.url.path}' tidak tersedia",
            "available_docs": "/docs"
        }
    )

@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    """Handle 500 Internal Server errors"""
    import traceback
    print("\n" + "=" * 80)
    print("🔴 500 INTERNAL SERVER ERROR:")
    print("=" * 80)
    print(f"Request: {request.method} {request.url.path}")
    print(f"Error: {str(exc)}")
    print("\nTraceback:")
    traceback.print_exc()
    print("=" * 80 + "\n")
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "status": "error",
            "message": "Internal server error",
            "detail": "Terjadi kesalahan pada server."
        }
    )

# ============================================================================
# GLOBAL OPTIONS HANDLER (CORS Preflight) - CRITICAL!
# ============================================================================

@app.options("/{full_path:path}")
async def options_handler(full_path: str):
    """
    Global OPTIONS handler for CORS preflight requests
    
    This handles all OPTIONS requests for CORS preflight checks.
    Must be defined BEFORE routers to intercept OPTIONS requests.
    
    Returns 200 OK with appropriate CORS headers.
    """
    return JSONResponse(
        status_code=200,
        content={"status": "ok", "method": "OPTIONS"},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, PATCH, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, Accept, Origin, User-Agent, X-Requested-With",
            "Access-Control-Max-Age": "3600",
            "Access-Control-Allow-Credentials": "true",
        }
    )

# ============================================================================
# ROUTERS
# ============================================================================

# Register all routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(questions.router)
app.include_router(materials.router)  # Materials management
app.include_router(sessions.router)
app.include_router(progress.router)
app.include_router(admin.router)
app.include_router(review.router)
app.include_router(exam.router)

# ============================================================================
# ROOT ENDPOINTS
# ============================================================================

@app.get("/", tags=["Root"])
def read_root():
    """
    Root endpoint - API information
    """
    return {
        "name": "ML Question System API",
        "version": "3.1.0",
        "status": "running",
        "features": [
            "NEVER REPEAT session system",
            "Exam mode (Premium only)",
            "Review mode for practice",
            "Materials management & ML question generation",
            "Tier-based access control (Free/Basic/Premium)",
            "4 role system (admin/cpns/polri/mixed)",
            "User statistics tracking",
            "Smart question selection",
            "Session history",
            "Admin user management"
        ],
        "docs": "/docs",
        "redoc": "/redoc",
        "endpoints": {
            "auth": "/auth - Authentication & authorization",
            "users": "/users - User management",
            "questions": "/questions - Question bank",
            "materials": "/materials - Materials management & ML generation",
            "sessions": "/sessions - Session management (NEVER REPEAT)",
            "exam": "/exam - Exam mode (Premium only)",
            "progress": "/progress - User progress tracking",
            "admin": "/admin - Admin functions (Admin only)",
            "review": "/api/review - Review sessions"
        }
    }

@app.get("/health", tags=["Root"])
def health_check():
    """
    Health check endpoint
    
    Used by monitoring tools to check if API is running
    """
    return {
        "status": "healthy",
        "service": "ml-question-api",
        "version": "3.1.0",
        "features": {
            "never_repeat": True,
            "review_mode": True,
            "exam_mode": True,
            "tier_system": True,
            "materials_management": True,
            "ml_generation": True,
            "user_stats": True,
            "session_history": True,
            "admin_panel": True
        }
    }

@app.get("/api/info", tags=["Root"])
def api_info():
    """
    Detailed API information
    
    Returns comprehensive information about available endpoints and features
    """
    return {
        "api": {
            "name": "ML Question System API",
            "version": "3.1.0",
            "description": "Backend API for POLRI & CPNS exam preparation with NEVER REPEAT system, Exam Mode, Materials Management, and ML Question Generation"
        },
        "features": {
            "session_management": {
                "never_repeat": "Users never see same question twice",
                "review_mode": "Practice past sessions anytime",
                "exam_mode": "Real exam simulation with mixed subjects (Premium only)",
                "smart_selection": "Priority: never used → least used → oldest"
            },
            "materials_management": {
                "input": "Add learning materials via web interface",
                "generation": "Generate questions using Gemini AI",
                "organization": "Tag and categorize by subject/difficulty",
                "quality_control": "Validate generated questions"
            },
            "tier_system": {
                "free": {
                    "practice": True,
                    "review": True,
                    "exam_mode": False,
                    "explanations": False,
                    "max_questions": 10
                },
                "basic": {
                    "practice": True,
                    "review": True,
                    "exam_mode": False,
                    "explanations": True,
                    "max_questions": 50
                },
                "premium": {
                    "practice": True,
                    "review": True,
                    "exam_mode": True,
                    "explanations": True,
                    "max_questions": 200
                }
            },
            "role_system": {
                "admin": "Full access + user management + materials management",
                "user_cpns": "CPNS questions only",
                "user_polri": "POLRI questions only",
                "user_mixed": "Both CPNS & POLRI"
            },
            "exam_mode": {
                "cpns": {
                    "subjects": ["TIU", "TWK", "TKP"],
                    "questions_per_subject": 50,
                    "total_questions": 150,
                    "time_limit_minutes": 120
                },
                "polri": {
                    "subjects": ["Bahasa Inggris", "Numerik", "TIU", "TWK"],
                    "questions_per_subject": 50,
                    "total_questions": 200,
                    "time_limit_minutes": 150
                }
            },
            "statistics": {
                "user_stats": "Lifetime questions seen, accuracy, etc.",
                "session_history": "All past completed sessions",
                "question_performance": "Track question difficulty and usage",
                "tier_stats": "Performance breakdown by tier"
            }
        },
        "endpoints": {
            "auth": {
                "POST /auth/login": "User login",
                "POST /auth/register": "User registration",
                "POST /auth/refresh": "Refresh token",
                "POST /auth/logout": "User logout"
            },
            "materials": {
                "GET /materials": "Get all materials",
                "POST /materials": "Create new material",
                "GET /materials/{id}": "Get material by ID",
                "PUT /materials/{id}": "Update material",
                "DELETE /materials/{id}": "Delete material",
                "POST /materials/{id}/generate": "Generate questions from material",
                "GET /materials/stats/overview": "Get materials statistics"
            },
            "sessions": {
                "POST /sessions/create": "Create NEW session (fresh questions)",
                "POST /sessions/create-review": "Create REVIEW session",
                "GET /sessions/availability": "Check available questions",
                "GET /sessions/stats": "User statistics",
                "GET /sessions/history": "Session history",
                "POST /sessions/{id}/start": "Start session",
                "POST /sessions/{id}/answer": "Submit answer",
                "POST /sessions/{id}/submit": "Complete session"
            },
            "exam": {
                "POST /exam/create": "Create exam session (PREMIUM ONLY)",
                "GET /exam/availability/{category}": "Check exam availability (PREMIUM ONLY)"
            },
            "review": {
                "GET /api/review/sessions": "List reviewable sessions",
                "POST /api/review/{id}/start": "Start review session",
                "GET /api/review/stats": "Review statistics"
            },
            "admin": {
                "GET /admin/users": "Get all users (ADMIN ONLY)",
                "POST /admin/users": "Create user (ADMIN ONLY)",
                "GET /admin/users/{id}": "Get user details (ADMIN ONLY)",
                "PUT /admin/users/{id}": "Update user (ADMIN ONLY)",
                "DELETE /admin/users/{id}": "Deactivate user (ADMIN ONLY)",
                "GET /admin/stats/overview": "System statistics (ADMIN ONLY)"
            }
        },
        "access_control": {
            "authentication": "JWT Bearer token required for all endpoints except /auth/login and /materials",
            "role_based": "Some endpoints restricted by user role (admin, user_cpns, user_polri, user_mixed)",
            "tier_based": "Features restricted by tier (free, basic, premium)",
            "examples": {
                "free_user": "Can practice (max 10q), review, no explanations, no exam mode",
                "basic_user": "Can practice (max 50q), review, has explanations, no exam mode",
                "premium_user": "Full access: practice (max 200q), review, explanations, exam mode",
                "admin_user": "Full system access + user management + materials management"
            }
        },
        "documentation": {
            "swagger": "/docs",
            "redoc": "/redoc"
        }
    }

@app.get("/api/tiers", tags=["Root"])
def get_tier_info():
    """
    Get detailed tier information and features
    """
    return {
        "status": "success",
        "data": {
            "tiers": {
                "free": {
                    "name": "Free",
                    "price": 0,
                    "features": {
                        "practice_mode": True,
                        "review_mode": True,
                        "exam_mode": False,
                        "explanations": False,
                        "max_questions_per_session": 10,
                        "statistics": True
                    },
                    "description": "Basic access for trying out the system"
                },
                "basic": {
                    "name": "Basic",
                    "price": 50000,
                    "features": {
                        "practice_mode": True,
                        "review_mode": True,
                        "exam_mode": False,
                        "explanations": True,
                        "max_questions_per_session": 50,
                        "statistics": True
                    },
                    "description": "Perfect for regular practice with explanations"
                },
                "premium": {
                    "name": "Premium",
                    "price": 100000,
                    "features": {
                        "practice_mode": True,
                        "review_mode": True,
                        "exam_mode": True,
                        "explanations": True,
                        "max_questions_per_session": 200,
                        "statistics": True,
                        "exam_simulation": True
                    },
                    "description": "Complete access with exam mode simulation"
                }
            }
        }
    }

# ============================================================================
# STARTUP & SHUTDOWN EVENTS
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Run on application startup"""
    print("\n" + "=" * 70)
    print("🚀 ML QUESTION SYSTEM API v3.1 - STARTING")
    print("=" * 70)
    print(f"Environment: {os.getenv('DEBUG', 'False')}")
    print(f"Host: {os.getenv('HOST', '0.0.0.0')}")
    print(f"Port: {os.getenv('PORT', '8000')}")
    print(f"CORS Origins: {cors_origins}")
    print("\n🎯 Features:")
    print("   ✅ NEVER REPEAT session system")
    print("   ✅ Exam mode (Premium only)")
    print("   ✅ Review mode for practice")
    print("   ✅ Materials management")
    print("   ✅ ML question generation (Gemini AI)")
    print("   ✅ Tier system (Free/Basic/Premium)")
    print("   ✅ 4 roles (admin/cpns/polri/mixed)")
    print("   ✅ User statistics tracking")
    print("   ✅ Session history")
    print("   ✅ Admin user management")
    print("\n💎 Tier Features:")
    print("   FREE: Max 10 questions, no explanations, no exam")
    print("   BASIC: Max 50 questions, has explanations, no exam")
    print("   PREMIUM: Max 200 questions, explanations, EXAM MODE")
    print("\n👥 User Roles:")
    print("   ADMIN: Full access + user + materials management")
    print("   USER_CPNS: CPNS questions only")
    print("   USER_POLRI: POLRI questions only")
    print("   USER_MIXED: Both CPNS & POLRI")
    print("\n📚 Materials Management:")
    print("   ✅ Web interface for material input")
    print("   ✅ ML question generation via Gemini")
    print("   ✅ Quality control & validation")
    print("   ✅ Tag & categorize materials")
    print("=" * 70)
    print("✅ API is ready!")
    print("📚 Docs: http://localhost:8000/docs")
    print("📖 ReDoc: http://localhost:8000/redoc")
    print("ℹ️  Info: http://localhost:8000/api/info")
    print("💎 Tiers: http://localhost:8000/api/tiers")
    print("📝 Materials: http://localhost:8000/materials")
    print("🌐 HTML files can be opened directly (file:// protocol supported)")
    print("=" * 70 + "\n")

@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown"""
    print("\n" + "=" * 70)
    print("🛑 ML QUESTION SYSTEM API - SHUTTING DOWN")
    print("=" * 70)
    print("✅ Cleanup completed")
    print("=" * 70 + "\n")

# ============================================================================
# RUN SERVER (Development)
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", 8000))
    DEBUG = os.getenv("DEBUG", "True").lower() == "true"
    
    uvicorn.run(
        "main:app",
        host=HOST,
        port=PORT,
        reload=DEBUG,
        log_level="info"
    )