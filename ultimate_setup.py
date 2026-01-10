"""
ULTIMATE DATABASE SETUP
- Auto-detects database name from .env
- Drops everything completely
- Creates fresh database
- No psql commands needed!
"""
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import sys
from pathlib import Path
import os

sys.path.append(str(Path(__file__).parent))

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except:
    pass

def get_db_config():
    """Get database config from environment"""
    return {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', 5432)),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', 'postgres'),
        'database': os.getenv('DB_NAME', 'ml_question_system')
    }

def ultimate_setup():
    """Complete database setup from scratch"""
    
    config = get_db_config()
    target_db = config['database']
    
    print("=" * 70)
    print("🚀 ULTIMATE DATABASE SETUP")
    print("=" * 70)
    print()
    print(f"📋 Configuration:")
    print(f"   Host: {config['host']}")
    print(f"   Port: {config['port']}")
    print(f"   User: {config['user']}")
    print(f"   Target Database: {target_db}")
    print()
    print("⚠️  WARNING: This will COMPLETELY DROP and RECREATE the database!")
    print()
    
    response = input("Continue? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        print("❌ Cancelled")
        return
    
    print()
    
    try:
        # ================================================================
        # STEP 1: DROP DATABASE COMPLETELY
        # ================================================================
        
        print("=" * 70)
        print("🗑️  STEP 1: DROPPING DATABASE")
        print("=" * 70)
        print()
        
        # Connect to 'postgres' database first
        conn = psycopg2.connect(
            host=config['host'],
            port=config['port'],
            user=config['user'],
            password=config['password'],
            database='postgres'  # Connect to default database
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Terminate all connections to target database
        print(f"🔌 Terminating connections to '{target_db}'...")
        cursor.execute(f"""
            SELECT pg_terminate_backend(pg_stat_activity.pid)
            FROM pg_stat_activity
            WHERE pg_stat_activity.datname = '{target_db}'
            AND pid <> pg_backend_pid()
        """)
        print("✅ Connections terminated")
        
        # Drop database
        print(f"🗑️  Dropping database '{target_db}'...")
        cursor.execute(f"DROP DATABASE IF EXISTS {target_db}")
        print("✅ Database dropped")
        print()
        
        # ================================================================
        # STEP 2: CREATE FRESH DATABASE
        # ================================================================
        
        print("=" * 70)
        print("📦 STEP 2: CREATING FRESH DATABASE")
        print("=" * 70)
        print()
        
        print(f"📦 Creating database '{target_db}'...")
        cursor.execute(f"CREATE DATABASE {target_db}")
        print("✅ Database created")
        
        cursor.close()
        conn.close()
        print()
        
        # ================================================================
        # STEP 3: CREATE TABLES
        # ================================================================
        
        print("=" * 70)
        print("📊 STEP 3: CREATING TABLES")
        print("=" * 70)
        print()
        
        from database import engine
        from models import Base
        from sqlalchemy import inspect
        
        print("📊 Creating all tables from models...")
        Base.metadata.create_all(bind=engine)
        
        # Verify
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        print(f"✅ Created {len(tables)} tables:")
        for table in tables:
            cols = len(inspector.get_columns(table))
            print(f"   ✅ {table} ({cols} columns)")
        print()
        
        # ================================================================
        # STEP 4: ADD EXAM MODE COLUMNS
        # ================================================================
        
        print("=" * 70)
        print("📝 STEP 4: ADDING EXAM MODE COLUMNS")
        print("=" * 70)
        print()
        
        from database import SessionLocal
        from sqlalchemy import text
        
        db = SessionLocal()
        
        def col_exists(table, column):
            try:
                cols = [c['name'] for c in inspector.get_columns(table)]
                return column in cols
            except:
                return False
        
        # Add to users table
        print("👤 Updating users table...")
        if not col_exists('users', 'branch_access'):
            db.execute(text("ALTER TABLE users ADD COLUMN branch_access VARCHAR(10) DEFAULT 'cpns'"))
            print("   ✅ Added branch_access")
        
        if not col_exists('users', 'session_count'):
            db.execute(text("ALTER TABLE users ADD COLUMN session_count INTEGER DEFAULT 0"))
            print("   ✅ Added session_count")
        
        # Add to sessions table
        print("\n📝 Updating sessions table...")
        exam_cols = {
            'is_exam_mode': 'BOOLEAN DEFAULT FALSE',
            'current_subject': 'VARCHAR(50)',
            'subject_order': 'JSONB',
            'time_per_subject': 'INTEGER DEFAULT 3600',
            'subject_times': 'JSONB'
        }
        
        for col, typ in exam_cols.items():
            if not col_exists('sessions', col):
                db.execute(text(f"ALTER TABLE sessions ADD COLUMN {col} {typ}"))
                print(f"   ✅ Added {col}")
        
        db.commit()
        print()
        
        # ================================================================
        # STEP 5: CREATE ADMIN USER
        # ================================================================
        
        print("=" * 70)
        print("👔 STEP 5: CREATING ADMIN USER")
        print("=" * 70)
        print()
        
        from models import User
        from core.security import get_password_hash
        
        print("👤 Creating admin user...")
        
        admin = User(
            username='admin',
            hashed_password=get_password_hash('admin123'),
            full_name='System Administrator',
            role='admin',
            tier='admin',  # ADMIN TIER
            test_type='mixed',
            branch_access='both',
            session_count=0,
            is_active=True
        )
        
        db.add(admin)
        db.commit()
        db.refresh(admin)
        
        print("✅ Admin user created!")
        print()
        
        db.close()
        
        # ================================================================
        # FINAL VERIFICATION
        # ================================================================
        
        print("=" * 70)
        print("🔍 FINAL VERIFICATION")
        print("=" * 70)
        print()
        
        db = SessionLocal()
        
        # Check tables
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"✅ Tables: {len(tables)}")
        for t in tables:
            print(f"   - {t}")
        print()
        
        # Check user columns
        user_cols = [c['name'] for c in inspector.get_columns('users')]
        print("✅ Users table columns:")
        for col in ['branch_access', 'session_count']:
            status = "✅" if col in user_cols else "❌"
            print(f"   {status} {col}")
        print()
        
        # Check session columns
        session_cols = [c['name'] for c in inspector.get_columns('sessions')]
        print("✅ Sessions table columns:")
        for col in ['is_exam_mode', 'current_subject', 'subject_order']:
            status = "✅" if col in session_cols else "❌"
            print(f"   {status} {col}")
        print()
        
        # Check admin user
        admin = db.query(User).filter(User.username == 'admin').first()
        if admin:
            print("✅ Admin user:")
            print(f"   Username: {admin.username}")
            print(f"   Tier: {admin.tier}")
            print(f"   Role: {admin.role}")
            print(f"   Branch: {admin.branch_access}")
            print(f"   Session Count: {admin.session_count}")
        else:
            print("❌ Admin user not found!")
        
        db.close()
        print()
        
        # ================================================================
        # SUCCESS!
        # ================================================================
        
        print("=" * 70)
        print("✅✅✅ SETUP COMPLETE! ✅✅✅")
        print("=" * 70)
        print()
        print("🔐 Login Credentials:")
        print("   Username: admin")
        print("   Password: admin123")
        print("   Tier: admin (Full Access + User Management)")
        print()
        print("🚀 Next Step:")
        print("   uvicorn main:app --reload")
        print()
        print("=" * 70)
        print()
        
    except psycopg2.OperationalError as e:
        print()
        print("=" * 70)
        print("❌ CONNECTION ERROR")
        print("=" * 70)
        print(f"Error: {e}")
        print()
        print("💡 Solutions:")
        print("   1. Check if PostgreSQL is running")
        print("   2. Check password in .env file")
        print("   3. Start PostgreSQL:")
        print("      net start postgresql-x64-14")
        print()
        
    except Exception as e:
        print()
        print("=" * 70)
        print("❌ ERROR OCCURRED")
        print("=" * 70)
        print(f"Error: {e}")
        print()
        import traceback
        traceback.print_exc()
        print()

if __name__ == "__main__":
    try:
        ultimate_setup()
    except KeyboardInterrupt:
        print("\n\n❌ Cancelled by user")