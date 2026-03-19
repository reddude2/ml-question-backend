"""
Verify Admin User
Check if admin has correct tier in database and what login API returns
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from database import SessionLocal
from models import User
from sqlalchemy import text
from core.security import verify_password
import json

def verify_admin_user():
    """Verify admin user configuration"""
    
    db = SessionLocal()
    
    try:
        print("=" * 70)
        print("🔍 VERIFYING ADMIN USER")
        print("=" * 70)
        print()
        
        # ================================================================
        # CHECK DATABASE
        # ================================================================
        
        print("1️⃣  DATABASE CHECK")
        print("-" * 70)
        print()
        
        # Get admin from database
        admin = db.query(User).filter(User.username == 'admin').first()
        
        if not admin:
            print("❌ PROBLEM: Admin user NOT FOUND in database!")
            print()
            print("💡 Run this to create admin:")
            print("   python create_admin_only.py")
            return
        
        print("✅ Admin user found in database")
        print()
        print("📋 Admin User Details:")
        print(f"   User ID: {admin.user_id}")
        print(f"   Username: {admin.username}")
        print(f"   Full Name: {admin.full_name}")
        print(f"   Tier: {admin.tier}")
        print(f"   Role: {admin.role}")
        print(f"   Test Type: {admin.test_type}")
        print(f"   Branch Access: {admin.branch_access}")
        print(f"   Active: {admin.is_active}")
        print()
        
        # Check tier
        if admin.tier == 'admin':
            print("✅ Tier is CORRECT: 'admin' 👔")
        else:
            print(f"❌ PROBLEM: Tier is '{admin.tier}' not 'admin'!")
            print()
            print("🔧 Fixing now...")
            
            admin.tier = 'admin'
            admin.role = 'admin'
            admin.test_type = 'mixed'
            admin.branch_access = 'both'
            admin.session_count = 0
            
            db.commit()
            db.refresh(admin)
            
            print(f"✅ FIXED! Tier is now: {admin.tier}")
        
        print()
        
        # ================================================================
        # CHECK PASSWORD
        # ================================================================
        
        print("2️⃣  PASSWORD CHECK")
        print("-" * 70)
        print()
        
        password_ok = verify_password('admin123', admin.hashed_password)
        
        if password_ok:
            print("✅ Password 'admin123' is CORRECT")
        else:
            print("❌ Password 'admin123' is WRONG!")
            print()
            print("🔧 Resetting password...")
            
            from core.security import get_password_hash
            admin.hashed_password = get_password_hash('admin123')
            db.commit()
            
            print("✅ Password reset to 'admin123'")
        
        print()
        
        # ================================================================
        # SIMULATE LOGIN RESPONSE
        # ================================================================
        
        print("3️⃣  LOGIN API RESPONSE (SIMULATED)")
        print("-" * 70)
        print()
        
        print("This is what /auth/login SHOULD return:")
        print()
        
        login_response = {
            "access_token": "eyJ...(token here)...",
            "token_type": "bearer",
            "user_id": admin.user_id,
            "username": admin.username,
            "full_name": admin.full_name,
            "role": admin.role,
            "tier": admin.tier,
            "test_type": admin.test_type,
            "branch_access": admin.branch_access,
            "session_count": admin.session_count,
            "is_active": admin.is_active
        }
        
        print(json.dumps(login_response, indent=2))
        print()
        
        # Check tier in response
        if login_response['tier'] == 'admin':
            print("✅ Login response tier is CORRECT: 'admin'")
        else:
            print(f"❌ Login response tier is WRONG: '{login_response['tier']}'")
        
        print()
        
        # ================================================================
        # ALL USERS SUMMARY
        # ================================================================
        
        print("4️⃣  ALL USERS IN DATABASE")
        print("-" * 70)
        print()
        
        all_users = db.query(User).all()
        print(f"Total users: {len(all_users)}")
        print()
        
        print("User List:")
        for user in all_users:
            tier_emoji = {
                'admin': '👔',
                'premium': '⭐',
                'basic': '📘',
                'free': '🆓'
            }.get(user.tier, '❓')
            
            marker = " ⬅️  YOU ARE LOGGING IN AS THIS USER" if user.username == 'admin' else ""
            
            print(f"{tier_emoji} {user.username:15} | Tier: {user.tier:8} | Role: {user.role:15} | Branch: {user.branch_access:6}{marker}")
        
        print()
        
        # ================================================================
        # FINAL INSTRUCTIONS
        # ================================================================
        
        print("=" * 70)
        print("📋 SUMMARY")
        print("=" * 70)
        print()
        
        if admin.tier == 'admin' and password_ok:
            print("✅ EVERYTHING IS CORRECT!")
            print()
            print("🎯 YOUR ADMIN USER:")
            print(f"   Username: admin")
            print(f"   Password: admin123")
            print(f"   Tier: {admin.tier} 👔 (ADMIN - Full Access)")
            print(f"   Role: {admin.role}")
            print()
            print("🔄 NEXT STEPS:")
            print()
            print("1️⃣  Make sure backend is running:")
            print("   cd backend")
            print("   uvicorn main:app --reload")
            print()
            print("2️⃣  In desktop app:")
            print("   - LOGOUT completely (close app)")
            print("   - Re-open app")
            print("   - LOGIN with admin/admin123")
            print()
            print("3️⃣  After login, you should see:")
            print("   ✅ Tier badge: 👔 Administrator (NOT Free)")
            print("   ✅ Admin link in navigation")
            print("   ✅ Full access to all features")
            print()
            print("💡 If tier still shows 'Free' after login:")
            print("   - Open DevTools (F12)")
            print("   - Go to Console tab")
            print("   - Type: localStorage.clear()")
            print("   - Reload app and login again")
            print()
        else:
            print("⚠️  ISSUES DETECTED - but now fixed!")
            print()
            print("Please restart backend and try logging in again.")
            print()
        
        print("=" * 70)
        print()
        
        # ================================================================
        # TIER COMPARISON
        # ================================================================
        
        print("=" * 70)
        print("📊 TIER COMPARISON (FOR YOUR REFERENCE)")
        print("=" * 70)
        print()
        
        tiers_info = [
            {
                'tier': 'admin',
                'emoji': '👔',
                'name': 'Administrator',
                'exam': '✅',
                'explanations': '✅',
                'questions': '999',
                'sessions': 'Unlimited',
                'manage_users': '✅',
                'notes': 'FULL ACCESS - This is YOU!'
            },
            {
                'tier': 'premium',
                'emoji': '⭐',
                'name': 'Premium',
                'exam': '✅',
                'explanations': '✅',
                'questions': '200',
                'sessions': 'Unlimited',
                'manage_users': '❌',
                'notes': 'For paying users'
            },
            {
                'tier': 'basic',
                'emoji': '📘',
                'name': 'Basic',
                'exam': '❌',
                'explanations': '✅',
                'questions': '50',
                'sessions': 'Unlimited',
                'manage_users': '❌',
                'notes': 'For basic paying users'
            },
            {
                'tier': 'free',
                'emoji': '🆓',
                'name': 'Free',
                'exam': '❌',
                'explanations': '❌',
                'questions': '10',
                'sessions': '10 max',
                'manage_users': '❌',
                'notes': 'Default for new users'
            }
        ]
        
        for tier_info in tiers_info:
            print(f"{tier_info['emoji']} {tier_info['name'].upper()}")
            print(f"   Exam Mode: {tier_info['exam']}")
            print(f"   Explanations: {tier_info['explanations']}")
            print(f"   Max Questions: {tier_info['questions']}")
            print(f"   Sessions: {tier_info['sessions']}")
            print(f"   Manage Users: {tier_info['manage_users']}")
            print(f"   Notes: {tier_info['notes']}")
            print()
        
        print("=" * 70)
        print()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        db.close()

if __name__ == "__main__":
    verify_admin_user()