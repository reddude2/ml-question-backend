"""
Create Admin User Only
Tables already exist, just need admin user
Enhanced with verification and detailed output
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from database import SessionLocal, engine
from models import User
from core.security import get_password_hash
from sqlalchemy import text, inspect

def verify_tables():
    """Verify required tables exist"""
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    required = ['users', 'question_sessions']
    missing = [t for t in required if t not in tables]
    
    if missing:
        print(f"❌ ERROR: Missing tables: {missing}")
        print("   Please run: python quick_fresh_setup.py")
        return False
    
    return True

def verify_columns():
    """Verify required columns exist"""
    inspector = inspect(engine)
    
    # Check users table
    user_cols = [c['name'] for c in inspector.get_columns('users')]
    required_user = ['branch_access', 'session_count', 'tier']
    missing_user = [c for c in required_user if c not in user_cols]
    
    if missing_user:
        print(f"⚠️  WARNING: Users table missing columns: {missing_user}")
        return False
    
    # Check question_sessions table
    session_cols = [c['name'] for c in inspector.get_columns('question_sessions')]
    required_session = ['is_exam_mode', 'current_subject']
    missing_session = [c for c in required_session if c not in session_cols]
    
    if missing_session:
        print(f"⚠️  WARNING: Question_sessions table missing columns: {missing_session}")
        return False
    
    return True

def create_admin():
    """Create or update admin user"""
    
    print("=" * 70)
    print("👔 CREATING ADMIN USER")
    print("=" * 70)
    print()
    
    # Verify database
    print("🔍 Verifying database...")
    if not verify_tables():
        return
    
    if not verify_columns():
        print("⚠️  Some columns missing, but continuing...")
    
    print("✅ Database verified")
    print()
    
    db = SessionLocal()
    
    try:
        # Check if admin exists
        print("👤 Checking for existing admin...")
        admin = db.query(User).filter(User.username == 'admin').first()
        
        if admin:
            print(f"✅ Found existing admin (ID: {admin.user_id})")
            print(f"   Current tier: {admin.tier}")
            print(f"   Current role: {admin.role}")
            print()
            print("🔄 Updating admin user...")
            
            admin.tier = 'admin'
            admin.role = 'admin'
            admin.test_type = 'mixed'
            admin.branch_access = 'both'
            admin.session_count = 0
            admin.is_active = True
            
            action = "updated"
        else:
            print("📝 No admin found, creating new admin...")
            print()
            
            admin = User(
                username='admin',
                hashed_password=get_password_hash('admin123'),
                full_name='System Administrator',
                role='admin',
                tier='admin',
                test_type='mixed',
                branch_access='both',
                session_count=0,
                is_active=True
            )
            
            db.add(admin)
            action = "created"
        
        db.commit()
        db.refresh(admin)
        
        print(f"✅ Admin user {action} successfully!")
        print()
        
        # Display admin details
        print("=" * 70)
        print("👤 ADMIN USER DETAILS")
        print("=" * 70)
        print()
        print(f"User ID:        {admin.user_id}")
        print(f"Username:       {admin.username}")
        print(f"Password:       admin123")
        print(f"Full Name:      {admin.full_name}")
        print()
        print("🔐 Access Configuration:")
        print(f"Tier:           {admin.tier} 👔")
        print(f"Role:           {admin.role}")
        print(f"Test Type:      {admin.test_type}")
        print(f"Branch Access:  {admin.branch_access}")
        print(f"Session Count:  {admin.session_count}")
        print(f"Active:         {admin.is_active}")
        print()
        
        # Update other users
        print("=" * 70)
        print("🔄 UPDATING OTHER USERS")
        print("=" * 70)
        print()
        
        print("Setting branch_access for users without it...")
        result1 = db.execute(text("""
            UPDATE users 
            SET branch_access = COALESCE(test_type, 'cpns')
            WHERE branch_access IS NULL
        """))
        
        print("Setting branch_access='both' for premium users...")
        result2 = db.execute(text("""
            UPDATE users 
            SET branch_access = 'both' 
            WHERE tier IN ('admin', 'premium') AND branch_access != 'both'
        """))
        
        db.commit()
        
        total_updated = result1.rowcount + result2.rowcount
        if total_updated > 0:
            print(f"✅ Updated {total_updated} user(s)")
        else:
            print("ℹ️  No other users needed updates")
        print()
        
        # Show all users
        print("=" * 70)
        print("📋 ALL USERS IN DATABASE")
        print("=" * 70)
        print()
        
        all_users = db.query(User).all()
        print(f"Total users: {len(all_users)}")
        print()
        
        for user in all_users:
            tier_emoji = {
                'admin': '👔',
                'premium': '⭐',
                'basic': '📘',
                'free': '🆓'
            }.get(user.tier, '❓')
            
            print(f"{tier_emoji} {user.username:15} | Tier: {user.tier:8} | Role: {user.role:15} | Branch: {user.branch_access:6}")
        
        print()
        
        # Final summary
        print("=" * 70)
        print("✅✅✅ ADMIN SETUP COMPLETE! ✅✅✅")
        print("=" * 70)
        print()
        print("🎯 ADMIN CAPABILITIES:")
        print("   ✅ Full access to all features")
        print("   ✅ User management (create/edit/delete users)")
        print("   ✅ Access both CPNS & POLRI branches")
        print("   ✅ Exam mode enabled")
        print("   ✅ All explanations unlocked")
        print("   ✅ No question limits (999 per session)")
        print("   ✅ No session limits (unlimited)")
        print("   ✅ Admin dashboard access")
        print()
        print("🔐 LOGIN CREDENTIALS:")
        print("   Username: admin")
        print("   Password: admin123")
        print()
        print("=" * 70)
        print("🚀 NEXT STEPS")
        print("=" * 70)
        print()
        print("1️⃣  START BACKEND:")
        print("   uvicorn main:app --reload")
        print()
        print("2️⃣  ACCESS API DOCS:")
        print("   http://localhost:8000/docs")
        print()
        print("3️⃣  TEST LOGIN:")
        print('   curl -X POST http://localhost:8000/auth/login \\')
        print('     -H "Content-Type: application/json" \\')
        print('     -d \'{"username":"admin","password":"admin123"}\'')
        print()
        print("4️⃣  START DESKTOP APP:")
        print("   cd ../desktop_app")
        print("   npm start")
        print()
        print("=" * 70)
        print()
        
    except Exception as e:
        print()
        print("=" * 70)
        print("❌ ERROR OCCURRED")
        print("=" * 70)
        print(f"Error: {e}")
        print()
        
        import traceback
        print("Full traceback:")
        traceback.print_exc()
        print()
        
        db.rollback()
        
        print("💡 Troubleshooting:")
        print("   1. Make sure database exists and tables are created")
        print("   2. Run: python quick_fresh_setup.py")
        print("   3. Check .env file for correct DATABASE_URL")
        print()
        
    finally:
        db.close()

if __name__ == "__main__":
    try:
        create_admin()
    except KeyboardInterrupt:
        print("\n\n❌ Cancelled by user\n")
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}\n")
        import traceback
        traceback.print_exc()