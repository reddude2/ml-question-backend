"""
Force Update Admin Tier
Update database and verify
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from database import SessionLocal
from models import User
from sqlalchemy import text

def force_update_admin():
    """Force update admin user to tier='admin'"""
    
    db = SessionLocal()
    
    try:
        print("=" * 70)
        print("🔧 FORCE UPDATE ADMIN TIER")
        print("=" * 70)
        print()
        
        # Find admin user
        print("🔍 Finding admin user...")
        admin = db.query(User).filter(User.username == 'admin').first()
        
        if not admin:
            print("❌ Admin user not found!")
            print("   Run: python create_admin_only.py")
            return
        
        print(f"✅ Found admin user (ID: {admin.user_id})")
        print()
        
        # Show current state
        print("📋 CURRENT STATE:")
        print(f"   Tier: {admin.tier}")
        print(f"   Role: {admin.role}")
        print(f"   Branch: {admin.branch_access}")
        print()
        
        # Force update
        print("🔧 Forcing update...")
        
        admin.tier = 'admin'
        admin.role = 'admin'
        admin.test_type = 'mixed'
        admin.branch_access = 'both'
        admin.session_count = 0
        admin.is_active = True
        
        db.commit()
        db.refresh(admin)
        
        print("✅ Database updated!")
        print()
        
        # Verify with direct SQL
        print("🔍 Verifying with direct SQL query...")
        result = db.execute(
            text("SELECT username, tier, role, branch_access FROM users WHERE username = 'admin'")
        ).fetchone()
        
        print("✅ VERIFIED IN DATABASE:")
        print(f"   Username: {result[0]}")
        print(f"   Tier: {result[1]}")
        print(f"   Role: {result[2]}")
        print(f"   Branch Access: {result[3]}")
        print()
        
        # Show all users
        print("=" * 70)
        print("📋 ALL USERS")
        print("=" * 70)
        print()
        
        all_users = db.query(User).all()
        
        for user in all_users:
            tier_emoji = {
                'admin': '👔',
                'premium': '⭐',
                'basic': '📘',
                'free': '🆓'
            }.get(user.tier, '❓')
            
            print(f"{tier_emoji} {user.username:15} | Tier: {user.tier:8} | Role: {user.role:15} | Branch: {user.branch_access:6}")
        
        print()
        
        # Instructions
        print("=" * 70)
        print("✅ DATABASE UPDATED!")
        print("=" * 70)
        print()
        print("🔄 NEXT STEPS:")
        print()
        print("1️⃣  LOGOUT dari desktop app (klik tombol Logout)")
        print()
        print("2️⃣  LOGIN ULANG dengan:")
        print("   Username: admin")
        print("   Password: admin123")
        print()
        print("3️⃣  Tier badge seharusnya berubah jadi: 👔 Administrator")
        print()
        print("=" * 70)
        print()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        
    finally:
        db.close()

if __name__ == "__main__":
    force_update_admin()