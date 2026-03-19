"""
Add Exam Mode Columns - Enhanced Version
Better error handling and verification
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from database import engine, SessionLocal
from sqlalchemy import text, inspect
import traceback

def table_exists(table_name: str) -> bool:
    """Check if table exists"""
    try:
        inspector = inspect(engine)
        return table_name in inspector.get_table_names()
    except:
        return False

def column_exists(table_name: str, column_name: str) -> bool:
    """Check if column exists in table"""
    try:
        inspector = inspect(engine)
        columns = [col['name'] for col in inspector.get_columns(table_name)]
        return column_name in columns
    except:
        return False

def add_exam_mode_columns():
    """Add exam mode columns to database"""
    
    db = SessionLocal()
    
    try:
        print("=" * 60)
        print("📊 ADDING EXAM MODE COLUMNS")
        print("=" * 60)
        print()
        
        # ================================================================
        # VERIFY TABLES EXIST
        # ================================================================
        
        print("🔍 Checking database...")
        
        # Test connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT current_database()"))
            db_name = result.scalar()
            print(f"✅ Connected to: {db_name}")
        print()
        
        # Check tables
        print("📋 Checking tables...")
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        print(f"Found {len(tables)} tables:")
        for table in tables:
            print(f"   - {table}")
        print()
        
        # Verify required tables
        required_tables = ['users', 'sessions']
        missing_tables = [t for t in required_tables if t not in tables]
        
        if missing_tables:
            print("❌ ERROR: Missing tables!")
            print(f"   Missing: {missing_tables}")
            print()
            print("💡 SOLUTION:")
            print("   1. Run: python init_db.py")
            print("   2. Then run this script again")
            print()
            return
        
        print("✅ Required tables exist")
        print()
        
        # ================================================================
        # ADD COLUMNS TO USERS TABLE
        # ================================================================
        
        print("👤 Updating USERS table...")
        print()
        
        # branch_access
        if not column_exists('users', 'branch_access'):
            print("  ➕ Adding branch_access...")
            db.execute(text("ALTER TABLE users ADD COLUMN branch_access VARCHAR(10) DEFAULT 'cpns'"))
            db.commit()
            print("  ✅ Added branch_access")
        else:
            print("  ⏭️  branch_access already exists")
        
        # session_count
        if not column_exists('users', 'session_count'):
            print("  ➕ Adding session_count...")
            db.execute(text("ALTER TABLE users ADD COLUMN session_count INTEGER DEFAULT 0"))
            db.commit()
            print("  ✅ Added session_count")
        else:
            print("  ⏭️  session_count already exists")
        
        print()
        
        # ================================================================
        # ADD COLUMNS TO SESSIONS TABLE
        # ================================================================
        
        print("📝 Updating SESSIONS table...")
        print()
        
        exam_columns = {
            'is_exam_mode': ("BOOLEAN", "FALSE"),
            'current_subject': ("VARCHAR(50)", "NULL"),
            'subject_order': ("JSONB", "NULL"),
            'time_per_subject': ("INTEGER", "3600"),
            'subject_times': ("JSONB", "NULL")
        }
        
        for col_name, (col_type, default) in exam_columns.items():
            if not column_exists('sessions', col_name):
                print(f"  ➕ Adding {col_name}...")
                sql = f"ALTER TABLE sessions ADD COLUMN {col_name} {col_type} DEFAULT {default}"
                db.execute(text(sql))
                db.commit()
                print(f"  ✅ Added {col_name}")
            else:
                print(f"  ⏭️  {col_name} already exists")
        
        print()
        
        # ================================================================
        # UPDATE EXISTING DATA
        # ================================================================
        
        print("🔄 Updating existing data...")
        
        # Update users
        db.execute(text("""
            UPDATE users 
            SET branch_access = COALESCE(test_type, 'cpns')
            WHERE branch_access IS NULL OR branch_access = ''
        """))
        
        db.execute(text("""
            UPDATE users 
            SET branch_access = 'both' 
            WHERE tier IN ('admin', 'premium')
        """))
        
        db.commit()
        print("✅ Data updated")
        print()
        
        # ================================================================
        # ADD CONSTRAINTS
        # ================================================================
        
        print("🔒 Adding constraints...")
        
        try:
            db.execute(text("ALTER TABLE users DROP CONSTRAINT IF EXISTS users_branch_access_check"))
            db.execute(text("ALTER TABLE users ADD CONSTRAINT users_branch_access_check CHECK (branch_access IN ('cpns', 'polri', 'both'))"))
            db.commit()
            print("✅ Constraints added")
        except Exception as e:
            print(f"⚠️  Constraints: {e}")
        
        print()
        
        # ================================================================
        # FINAL VERIFICATION
        # ================================================================
        
        print("=" * 60)
        print("🔍 FINAL VERIFICATION")
        print("=" * 60)
        print()
        
        inspector = inspect(engine)
        
        # Check users table
        print("Users table columns:")
        user_cols = [col['name'] for col in inspector.get_columns('users')]
        for col in ['branch_access', 'session_count']:
            status = "✅" if col in user_cols else "❌"
            print(f"   {status} {col}")
        
        print()
        
        # Check sessions table
        print("Sessions table columns:")
        session_cols = [col['name'] for col in inspector.get_columns('sessions')]
        for col in ['is_exam_mode', 'current_subject', 'subject_order', 'time_per_subject', 'subject_times']:
            status = "✅" if col in session_cols else "❌"
            print(f"   {status} {col}")
        
        print()
        print("=" * 60)
        print("✅✅✅ MIGRATION COMPLETE! ✅✅✅")
        print("=" * 60)
        print()
        print("🔄 NEXT STEP:")
        print("   Run: python create_admin_tier.py")
        print()
        
    except Exception as e:
        print()
        print("=" * 60)
        print("❌ ERROR")
        print("=" * 60)
        print(f"Error: {e}")
        print()
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    add_exam_mode_columns()