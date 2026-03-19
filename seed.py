"""
Database Seeding Script
"""

from database import SessionLocal, init_db
from models import User, Question, UserProgress
from core.security import hash_password
from datetime import datetime, timezone, timedelta

def seed_all():
    print("=" * 60)
    print("🌱 SEEDING DATABASE")
    print("=" * 60)
    
    init_db()
    print("✅ Tables created")
    
    db = SessionLocal()
    
    try:
        # Admin user
        if not db.query(User).filter(User.username == "admin").first():
            now = datetime.now(timezone.utc)
            admin = User(
                username="admin",
                hashed_password=hash_password("admin123"),
                full_name="Administrator",
                role="admin",
                test_type="campur",
                tier="premium",
                is_active=True,
                subscription_start=now,
                subscription_end=now + timedelta(days=3650)
            )
            db.add(admin)
            db.flush()
            
            admin_progress = UserProgress(
                user_id=admin.user_id,
                total_sessions=0,
                total_questions=0,
                total_correct=0,
                overall_accuracy=0.0,
                subject_stats={},
                last_activity=now
            )
            db.add(admin_progress)
            print("✅ Admin created (admin/admin123)")
        
        # Sample users
        sample_users = [
            {"username": "polri_user", "password": "polri123", "full_name": "User POLRI", "test_type": "polri", "tier": "free"},
            {"username": "cpns_user", "password": "cpns123", "full_name": "User CPNS", "test_type": "cpns", "tier": "basic"},
            {"username": "premium_user", "password": "premium123", "full_name": "User Premium", "test_type": "campur", "tier": "premium"}
        ]
        
        for u in sample_users:
            if not db.query(User).filter(User.username == u["username"]).first():
                now = datetime.now(timezone.utc)
                user = User(
                    username=u["username"],
                    hashed_password=hash_password(u["password"]),
                    full_name=u["full_name"],
                    role="user",
                    test_type=u["test_type"],
                    tier=u["tier"],
                    is_active=True,
                    subscription_start=now,
                    subscription_end=now + timedelta(days=30)
                )
                db.add(user)
                db.flush()
                
                progress = UserProgress(
                    user_id=user.user_id,
                    total_sessions=0,
                    total_questions=0,
                    total_correct=0,
                    overall_accuracy=0.0,
                    subject_stats={},
                    last_activity=now
                )
                db.add(progress)
                print(f"✅ Created {u['username']} ({u['password']})")
        
        # Sample questions
        questions = [
            {
                "question_id": "q_cpns_tiu_001",
                "test_category": "cpns",
                "subject": "tiu",
                "subtype": "verbal",
                "difficulty": "mudah",
                "question_text": "Sinonim dari kata 'CEMERLANG' adalah...",
                "options": {"A": "Gemilang", "B": "Suram", "C": "Kusam", "D": "Pudar", "E": "Redup"},
                "correct_answer": "A",
                "explanation": "Cemerlang berarti sangat terang atau bersinar.",
                "explanation_tier": "free"
            },
            {
                "question_id": "q_polri_eng_001",
                "test_category": "polri",
                "subject": "bahasa_inggris",
                "subtype": None,
                "difficulty": "mudah",
                "question_text": "The opposite of 'difficult' is...",
                "options": {"A": "Hard", "B": "Easy", "C": "Complex", "D": "Tough", "E": "Complicated"},
                "correct_answer": "B",
                "explanation": "Opposite (antonim) dari 'difficult' adalah 'easy'.",
                "explanation_tier": "free"
            }
        ]
        
        for q in questions:
            if not db.query(Question).filter(Question.question_id == q["question_id"]).first():
                question = Question(**q)
                db.add(question)
                print(f"✅ Created {q['question_id']}")
        
        db.commit()
        
        print("=" * 60)
        print(f"Total users: {db.query(User).count()}")
        print(f"Total questions: {db.query(Question).count()}")
        print("=" * 60)
        print("✅ Seeding completed!")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_all()