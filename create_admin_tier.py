"""
Create or Update Admin User with tier='admin'
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from database import SessionLocal
from models import User
from core.security import get_password_hash
from sqlalchemy import text

def create_admin():
    """Create or update admin user"""
    
    db = SessionLocal()
    
    try:
        print("=" * 60)
        print("👔 CREATING ADMIN USER (tier='admin')")
        print("=" * 60)
        print()
        
        # Check if admin exists
        admin = db.query(User).filter(User.username == 'admin').first()
        
        if admin:
            print("✅ Found existing admin")
            print(f"   Current tier: {admin.tier}")
            print()
            print("🔄 Updating to tier='admin'...")
            
            admin.tier = 'admin'
            admin.role = 'admin'
            admin.test_type = 'mixed'
            admin.branch_access = 'both'
            admin.session_count = 0
            admin.is_active = True
            
        else:
            print("📝 Creating new admin user...")
            
            admin = User(
                username='admin',
                hashed_password=get_password_hash('admin123'),
                full_name='System Administrator',
                role='admin',
                tier='admin',  # ADMIN TIER!
                test_type='mixed',
                branch_access='both',
                session_count=0,
                is_active=True
            )
            db.add(admin)
        
        db.commit()
        db.refresh(admin)
        
        print()
        print("=" * 60)
        print("✅ ADMIN USER READY!")
        print("=" * 60)
        print(f"Username: {admin.username}")
        print(f"Password: admin123")
        print(f"Tier: {admin.tier} 👔")
        print(f"Role: {admin.role}")
        print(f"Branch Access: {admin.branch_access}")
        print(f"Session Count: {admin.session_count}")
        print()
        
        # Verify with SQL
        result = db.execute(text("SELECT tier, role, branch_access FROM users WHERE username = 'admin'"))
        row = result.fetchone()
        
        print("=" * 60)
        print("🔍 DATABASE VERIFICATION")
        print("=" * 60)
        print(f"Tier: {row[0]}")
        print(f"Role: {row[1]}")
        print(f"Branch: {row[2]}")
        print()
        
        if row[0] == 'admin':
            print("✅✅✅ SUCCESS! ADMIN TIER CREATED! ✅✅✅")
        else:
            print(f"❌ FAILED! Tier is: {row[0]}")
        
        print("=" * 60)
        print()
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_admin()