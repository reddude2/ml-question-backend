"""
FINAL SETUP - Parses DATABASE_URL from .env
Works with your exact .env format
"""
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import sys
from pathlib import Path
import re

sys.path.append(str(Path(__file__).parent))

def parse_database_url():
    """Parse DATABASE_URL from .env"""
    try:
        from dotenv import load_dotenv
        import os
        load_dotenv()
        
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            raise ValueError("DATABASE_URL not found in .env")
        
        # Parse postgresql://user:password@host:port/database
        pattern = r'postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)'
        match = re.match(pattern, database_url)
        
        if not match:
            raise ValueError("Invalid DATABASE_URL format")
        
        user, password, host, port, database = match.groups()
        
        return {
            'user': user,
            'password': password,
            'host': host,
            'port': int(port),
            'database': database
        }
    except ImportError:
        # Fallback if dotenv not installed
        return {
            'user': 'postgres',
            'password': 'admin123',
            'host': 'localhost',
            'port': 5432,
            'database': 'ml_question_system'
        }

def final_setup():
    """Complete database setup"""
    
    config = parse_database_url()
    
    print("=" * 70)
    print("🚀 FINAL DATABASE SETUP")
    print("=" * 70)
    print()
    print("📋 Configuration from .env:")
    print(f"   User: {config['user']}")
    print(f"   Host: {config['host']}")
    print(f"   Port: {config['port']}")
    print(f"   Database: {config['database']}")
    print(f"   Password: {'*' * len(config['password'])}")
    print()
    print("⚠️  This will DROP and RECREATE the database!")
    print()
    
    response = input("Continue? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        print("❌ Cancelled")
        return
    
    print()
    
    try:
        # ================================================================
        # STEP 1: DROP DATABASE
        # ================================================================
        
        print("=" * 70)
        print("🗑️  STEP 1: DROPPING DATABASE")
        print("=" * 70)
        print()
        
        print("🔌 Connecting to PostgreSQL...")
        conn = psycopg2.connect(
            host=config['host'],
            port=config['port'],
            user=config['user'],
            password=config['password'],
            database='postgres'
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        print("✅ Connected successfully!")
        print()
        
        # Terminate connections
        print(f"🔌 Terminating connections to '{config['database']}'...")
        cursor.execute(f"""
            SELECT pg_terminate_backend(pg_stat_activity.pid)
            FROM pg_stat_activity
            WHERE pg_stat_activity.datname = '{config['database']}'
            AND pid <> pg_backend_pid()
        """)
        print("✅ Connections terminated")
        
        # Drop database
        print(f"🗑️  Dropping database '{config['database']}'...")
        cursor.execute(f"DROP DATABASE IF EXISTS {config['database']}")
        print("✅ Database dropped")
        print()
        
        # ================================================================
        # STEP 2: CREATE DATABASE
        # ================================================================
        
        print("=" * 70)
        print("📦 STEP 2: CREATING FRESH DATABASE")
        print("=" * 70)
        print()
        
        print(f"📦 Creating database '{config['database']}'...")
        cursor.execute(f"CREATE DATABASE {config['database']}")
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
        
        print("📊 Creating all tables...")
        Base.metadata.create_all(bind=engine)
        
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        print(f"✅ Created {len(tables)} tables:")
        for table in sorted(tables):
            cols = len(inspector.get_columns(table))
            print(f"   ✅ {table} ({cols} columns)")
        print()
        
        # ================================================================
        # STEP 4: ADD EXAM COLUMNS
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
        
        # Users table
        print("👤 Updating users table...")
        added = []
        
        if not col_exists('users', 'branch_access'):
            db.execute(text("ALTER TABLE users ADD COLUMN branch_access VARCHAR(10) DEFAULT 'cpns'"))
            added.append('branch_access')
        
        if not col_exists('users', 'session_count'):
            db.execute(text("ALTER TABLE users ADD COLUMN session_count INTEGER DEFAULT 0"))
            added.append('session_count')
        
        if added:
            print(f"   ✅ Added: {', '.join(added)}")
        else:
            print("   ⏭️  All columns exist")
        print()
        
        # Sessions table
        print("📝 Updating sessions table...")
        exam_cols = {
            'is_exam_mode': 'BOOLEAN DEFAULT FALSE',
            'current_subject': 'VARCHAR(50)',
            'subject_order': 'JSONB',
            'time_per_subject': 'INTEGER DEFAULT 3600',
            'subject_times': 'JSONB'
        }
        
        added = []
        for col, typ in exam_cols.items():
            if not col_exists('sessions', col):
                db.execute(text(f"ALTER TABLE sessions ADD COLUMN {col} {typ}"))
                added.append(col)
        
        if added:
            print(f"   ✅ Added: {', '.join(added)}")
        else:
            print("   ⏭️  All columns exist")
        
        db.commit()
        print()
        
        # ================================================================
        # STEP 5: CREATE ADMIN
        # ================================================================
        
        print("=" * 70)
        print("👔 STEP 5: CREATING ADMIN USER")
        print("=" * 70)
        print()
        
        from models import User
        from core.security import get_password_hash
        
        print("👤 Creating admin user with tier='admin'...")
        
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
        
        # Update existing users (if any)
        db.execute(text("UPDATE users SET branch_access = COALESCE(test_type, 'cpns') WHERE branch_access IS NULL"))
        db.execute(text("UPDATE users SET branch_access = 'both' WHERE tier IN ('admin', 'premium')"))
        db.commit()
        
        db.close()
        
        # ================================================================
        # STEP 6: VERIFICATION
        # ================================================================
        
        print("=" * 70)
        print("🔍 FINAL VERIFICATION")
        print("=" * 70)
        print()
        
        db = SessionLocal()
        inspector = inspect(engine)
        
        # Check tables
        tables = inspector.get_table_names()
        print(f"✅ Total tables: {len(tables)}")
        print()
        
        # Check users columns
        user_cols = [c['name'] for c in inspector.get_columns('users')]
        print("✅ Users table:")
        for col in ['username', 'tier', 'role', 'branch_access', 'session_count']:
            status = "✅" if col in user_cols else "❌"
            print(f"   {status} {col}")
        print()
        
        # Check sessions columns
        session_cols = [c['name'] for c in inspector.get_columns('sessions')]
        print("✅ Sessions table:")
        for col in ['session_id', 'is_exam_mode', 'current_subject', 'subject_order']:
            status = "✅" if col in session_cols else "❌"
            print(f"   {status} {col}")
        print()
        
        # Check admin user
        admin = db.query(User).filter(User.username == 'admin').first()
        if admin:
            print("✅ Admin User:")
            print(f"   Username: {admin.username}")
            print(f"   Tier: {admin.tier} 👔")
            print(f"   Role: {admin.role}")
            print(f"   Branch Access: {admin.branch_access}")
            print(f"   Session Count: {admin.session_count}")
            print(f"   Active: {admin.is_active}")
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
        print("🎯 SYSTEM READY!")
        print()
        print("🔐 Login Credentials:")
        print("   Username: admin")
        print("   Password: admin123")
        print("   Tier: admin (Full Access)")
        print()
        print("📊 Database Info:")
        print(f"   Database: {config['database']}")
        print(f"   Tables: {len(tables)}")
        print(f"   Host: {config['host']}:{config['port']}")
        print()
        print("🚀 Next Step - Start Backend:")
        print("   cd backend")
        print("   uvicorn main:app --reload")
        print()
        print("🌐 Then access:")
        print("   Backend API: http://localhost:8000")
        print("   API Docs: http://localhost:8000/docs")
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
        print("💡 Check:")
        print("   1. PostgreSQL is running: net start postgresql-x64-14")
        print("   2. Password in .env is correct")
        print("   3. User 'postgres' exists and has permissions")
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
        final_setup()
    except KeyboardInterrupt:
        print("\n\n❌ Cancelled by user\n")