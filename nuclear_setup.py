"""
NUCLEAR DATABASE SETUP
Absolutely guarantees database is dropped and recreated
No mercy - kills everything!
"""
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import sys
from pathlib import Path
import re
import time

sys.path.append(str(Path(__file__).parent))

def parse_database_url():
    """Parse DATABASE_URL from .env"""
    try:
        from dotenv import load_dotenv
        import os
        load_dotenv()
        
        database_url = os.getenv('DATABASE_URL')
        pattern = r'postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)'
        match = re.match(pattern, database_url)
        
        if match:
            user, password, host, port, database = match.groups()
            return {
                'user': user,
                'password': password,
                'host': host,
                'port': int(port),
                'database': database
            }
    except:
        pass
    
    return {
        'user': 'postgres',
        'password': 'admin123',
        'host': 'localhost',
        'port': 5432,
        'database': 'ml_question_system'
    }

def nuclear_setup():
    """Nuclear option - absolutely guarantees clean database"""
    
    config = parse_database_url()
    target_db = config['database']
    
    print("=" * 70)
    print("💣 NUCLEAR DATABASE SETUP 💣")
    print("=" * 70)
    print()
    print("⚠️  WARNING: This will FORCEFULLY drop and recreate everything!")
    print(f"   Target: {target_db}")
    print()
    
    response = input("Continue with NUCLEAR option? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        print("❌ Cancelled")
        return
    
    print()
    
    try:
        # ================================================================
        # PHASE 1: NUCLEAR DROP
        # ================================================================
        
        print("=" * 70)
        print("💣 PHASE 1: NUCLEAR DROP")
        print("=" * 70)
        print()
        
        print("🔌 Connecting to postgres database...")
        conn = psycopg2.connect(
            host=config['host'],
            port=config['port'],
            user=config['user'],
            password=config['password'],
            database='postgres'  # IMPORTANT: Connect to postgres, NOT target!
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        print("✅ Connected to 'postgres' database")
        print()
        
        # Step 1: Revoke connections
        print(f"🔒 Step 1: Revoking CONNECT privilege from '{target_db}'...")
        cursor.execute(f"REVOKE CONNECT ON DATABASE {target_db} FROM public")
        print("✅ Revoked")
        
        # Step 2: Terminate ALL connections
        print(f"🔌 Step 2: Terminating ALL connections to '{target_db}'...")
        cursor.execute(f"""
            SELECT pg_terminate_backend(pid)
            FROM pg_stat_activity
            WHERE datname = '{target_db}'
            AND pid <> pg_backend_pid()
        """)
        result = cursor.fetchall()
        print(f"✅ Terminated {len(result)} connections")
        
        # Give it a moment
        time.sleep(1)
        
        # Step 3: Try DROP with FORCE (PostgreSQL 13+)
        print(f"💣 Step 3: Dropping database WITH FORCE...")
        try:
            cursor.execute(f"DROP DATABASE IF EXISTS {target_db} WITH (FORCE)")
            print("✅ Database dropped with FORCE")
        except Exception as e:
            # Fallback to regular drop if FORCE not supported
            print(f"⚠️  FORCE not supported, trying regular drop...")
            cursor.execute(f"DROP DATABASE IF EXISTS {target_db}")
            print("✅ Database dropped")
        
        print()
        
        # Step 4: Verify it's gone
        print("🔍 Step 4: Verifying database is gone...")
        cursor.execute("SELECT datname FROM pg_database WHERE datname = %s", (target_db,))
        if cursor.fetchone():
            print("❌ ERROR: Database still exists!")
            print()
            print("💡 MANUAL FIX REQUIRED:")
            print("   1. Close ALL programs using PostgreSQL")
            print("   2. Restart PostgreSQL service")
            print("   3. Run this script again")
            return
        else:
            print("✅ Database completely removed")
        
        print()
        
        # ================================================================
        # PHASE 2: CREATE FRESH
        # ================================================================
        
        print("=" * 70)
        print("📦 PHASE 2: CREATE FRESH DATABASE")
        print("=" * 70)
        print()
        
        print(f"📦 Creating database '{target_db}'...")
        cursor.execute(f"CREATE DATABASE {target_db}")
        print("✅ Database created")
        
        # Grant permissions
        print("🔓 Granting permissions...")
        cursor.execute(f"GRANT ALL PRIVILEGES ON DATABASE {target_db} TO {config['user']}")
        print("✅ Permissions granted")
        
        cursor.close()
        conn.close()
        
        print()
        
        # ================================================================
        # PHASE 3: CREATE TABLES
        # ================================================================
        
        print("=" * 70)
        print("📊 PHASE 3: CREATE TABLES")
        print("=" * 70)
        print()
        
        # Force reload database module to use new database
        import importlib
        import database
        importlib.reload(database)
        
        from database import engine
        from models import Base
        from sqlalchemy import inspect
        
        print("📊 Creating all tables from models...")
        
        try:
            Base.metadata.create_all(bind=engine, checkfirst=True)
            print("✅ Tables created")
        except Exception as e:
            print(f"❌ Error: {e}")
            print()
            print("💡 Trying manual table creation...")
            
            # Manual cleanup if needed
            with engine.connect() as conn:
                conn.execute(text("DROP SCHEMA public CASCADE"))
                conn.execute(text("CREATE SCHEMA public"))
                conn.execute(text("GRANT ALL ON SCHEMA public TO postgres"))
                conn.execute(text("GRANT ALL ON SCHEMA public TO public"))
                conn.commit()
            
            Base.metadata.create_all(bind=engine)
            print("✅ Tables created (manual cleanup)")
        
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        print()
        print(f"✅ Created {len(tables)} tables:")
        for table in sorted(tables):
            cols = len(inspector.get_columns(table))
            print(f"   ✅ {table} ({cols} columns)")
        print()
        
        # ================================================================
        # PHASE 4: ADD EXAM COLUMNS
        # ================================================================
        
        print("=" * 70)
        print("📝 PHASE 4: ADD EXAM COLUMNS")
        print("=" * 70)
        print()
        
        from database import SessionLocal
        from sqlalchemy import text
        
        db = SessionLocal()
        
        def col_exists(table, column):
            cols = [c['name'] for c in inspector.get_columns(table)]
            return column in cols
        
        # Users
        print("👤 Users table...")
        if not col_exists('users', 'branch_access'):
            db.execute(text("ALTER TABLE users ADD COLUMN branch_access VARCHAR(10) DEFAULT 'cpns'"))
            print("   ✅ branch_access")
        if not col_exists('users', 'session_count'):
            db.execute(text("ALTER TABLE users ADD COLUMN session_count INTEGER DEFAULT 0"))
            print("   ✅ session_count")
        
        # Sessions
        print("\n📝 Sessions table...")
        exams = {
            'is_exam_mode': 'BOOLEAN DEFAULT FALSE',
            'current_subject': 'VARCHAR(50)',
            'subject_order': 'JSONB',
            'time_per_subject': 'INTEGER DEFAULT 3600',
            'subject_times': 'JSONB'
        }
        
        for col, typ in exams.items():
            if not col_exists('sessions', col):
                db.execute(text(f"ALTER TABLE sessions ADD COLUMN {col} {typ}"))
                print(f"   ✅ {col}")
        
        db.commit()
        print()
        
        # ================================================================
        # PHASE 5: CREATE ADMIN
        # ================================================================
        
        print("=" * 70)
        print("👔 PHASE 5: CREATE ADMIN")
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
            tier='admin',
            test_type='mixed',
            branch_access='both',
            session_count=0,
            is_active=True
        )
        
        db.add(admin)
        db.commit()
        db.refresh(admin)
        
        print("✅ Admin created")
        print()
        
        db.close()
        
        # ================================================================
        # VERIFICATION
        # ================================================================
        
        print("=" * 70)
        print("🔍 FINAL VERIFICATION")
        print("=" * 70)
        print()
        
        db = SessionLocal()
        
        # Verify admin
        admin = db.query(User).filter(User.username == 'admin').first()
        if admin:
            print("✅ Admin User:")
            print(f"   Username: {admin.username}")
            print(f"   Tier: {admin.tier} 👔")
            print(f"   Branch: {admin.branch_access}")
        
        db.close()
        print()
        
        # ================================================================
        # SUCCESS
        # ================================================================
        
        print("=" * 70)
        print("✅✅✅ NUCLEAR SETUP COMPLETE! ✅✅✅")
        print("=" * 70)
        print()
        print("🎯 Database: {target_db}")
        print(f"📊 Tables: {len(tables)}")
        print()
        print("🔐 Login:")
        print("   admin / admin123")
        print()
        print("🚀 Start backend:")
        print("   uvicorn main:app --reload")
        print()
        print("=" * 70)
        print()
        
    except Exception as e:
        print()
        print("=" * 70)
        print("❌ ERROR")
        print("=" * 70)
        print(f"{e}")
        print()
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    nuclear_setup()