"""
QUICK FRESH SETUP
Clean database setup with all features
- Parses DATABASE_URL from .env
- Drops and recreates database
- Creates all tables
- Adds exam mode columns
- Creates admin user with tier='admin'
"""

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import sys
from pathlib import Path
import re
import time

sys.path.append(str(Path(__file__).parent))

def parse_database_url():
    """Parse DATABASE_URL from .env file"""
    try:
        from dotenv import load_dotenv
        import os
        load_dotenv()
        
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            print("⚠️  DATABASE_URL not found in .env, using defaults")
            return None
        
        # Parse postgresql://user:password@host:port/database
        pattern = r'postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)'
        match = re.match(pattern, database_url)
        
        if not match:
            print("⚠️  Invalid DATABASE_URL format, using defaults")
            return None
        
        user, password, host, port, database = match.groups()
        
        return {
            'user': user,
            'password': password,
            'host': host,
            'port': int(port),
            'database': database
        }
    except ImportError:
        print("⚠️  python-dotenv not installed, using defaults")
        return None
    except Exception as e:
        print(f"⚠️  Error parsing .env: {e}")
        return None

def get_config():
    """Get database configuration"""
    config = parse_database_url()
    
    if not config:
        # Default configuration
        config = {
            'user': 'postgres',
            'password': 'admin123',
            'host': 'localhost',
            'port': 5432,
            'database': 'ml_question_system'
        }
        print("📋 Using default configuration")
    else:
        print("📋 Using configuration from .env")
    
    return config

def quick_fresh_setup():
    """Complete fresh database setup"""
    
    print("=" * 70)
    print("🚀 QUICK FRESH DATABASE SETUP")
    print("=" * 70)
    print()
    
    config = get_config()
    target_db = config['database']
    
    print("📋 Configuration:")
    print(f"   Host: {config['host']}:{config['port']}")
    print(f"   User: {config['user']}")
    print(f"   Database: {target_db}")
    print(f"   Password: {'*' * len(config['password'])}")
    print()
    
    print("⚠️  WARNING: This will completely DROP and RECREATE the database!")
    print()
    
    response = input("Continue? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        print("❌ Cancelled")
        return
    
    print()
    
    try:
        # ================================================================
        # PHASE 1: DROP DATABASE
        # ================================================================
        
        print("=" * 70)
        print("💣 PHASE 1: DROPPING DATABASE")
        print("=" * 70)
        print()
        
        print("🔌 Connecting to PostgreSQL...")
        
        # Connect to 'postgres' database (not the target database)
        conn = psycopg2.connect(
            host=config['host'],
            port=config['port'],
            user=config['user'],
            password=config['password'],
            database='postgres'  # Important: Connect to postgres, not target!
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        print(f"✅ Connected to PostgreSQL server")
        print()
        
        # Check if database exists
        cursor.execute("SELECT datname FROM pg_database WHERE datname = %s", (target_db,))
        db_exists = cursor.fetchone()
        
        if db_exists:
            print(f"🔍 Database '{target_db}' exists")
            
            # Terminate all connections
            print("🔌 Terminating active connections...")
            cursor.execute(f"""
                SELECT pg_terminate_backend(pid)
                FROM pg_stat_activity
                WHERE datname = '{target_db}'
                AND pid <> pg_backend_pid()
            """)
            terminated = cursor.fetchall()
            print(f"✅ Terminated {len(terminated)} connections")
            
            # Wait a moment
            time.sleep(0.5)
            
            # Drop database
            print(f"💣 Dropping database '{target_db}'...")
            try:
                # Try WITH FORCE (PostgreSQL 13+)
                cursor.execute(f"DROP DATABASE IF EXISTS {target_db} WITH (FORCE)")
                print("✅ Database dropped (with FORCE)")
            except Exception:
                # Fallback to regular drop
                cursor.execute(f"DROP DATABASE IF EXISTS {target_db}")
                print("✅ Database dropped")
        else:
            print(f"ℹ️  Database '{target_db}' doesn't exist (will create new)")
        
        print()
        
        # ================================================================
        # PHASE 2: CREATE DATABASE
        # ================================================================
        
        print("=" * 70)
        print("📦 PHASE 2: CREATING FRESH DATABASE")
        print("=" * 70)
        print()
        
        print(f"📦 Creating database '{target_db}'...")
        cursor.execute(f"CREATE DATABASE {target_db}")
        print("✅ Database created")
        
        # Grant permissions
        print("🔓 Granting permissions...")
        cursor.execute(f"GRANT ALL PRIVILEGES ON DATABASE {target_db} TO {config['user']}")
        print("✅ Permissions granted")
        
        # Close connection to postgres database
        cursor.close()
        conn.close()
        
        print()
        
        # Small delay to ensure database is ready
        time.sleep(0.5)
        
        # ================================================================
        # PHASE 3: CREATE TABLES
        # ================================================================
        
        print("=" * 70)
        print("📊 PHASE 3: CREATING TABLES")
        print("=" * 70)
        print()
        
        print("📦 Importing models...")
        from database import engine
        from models import Base
        from sqlalchemy import inspect
        
        print("✅ Models imported")
        print()
        
        print("📊 Creating all tables from models...")
        Base.metadata.create_all(bind=engine)
        print("✅ Tables created")
        print()
        
        # Verify tables
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        print(f"✅ Created {len(tables)} tables:")
        for table in sorted(tables):
            cols = len(inspector.get_columns(table))
            print(f"   ✅ {table} ({cols} columns)")
        print()
        
        # ================================================================
        # PHASE 4: ADD EXAM MODE COLUMNS
        # ================================================================
        
        print("=" * 70)
        print("📝 PHASE 4: ADDING EXAM MODE COLUMNS")
        print("=" * 70)
        print()
        
        from database import SessionLocal
        from sqlalchemy import text
        
        db = SessionLocal()
        
        def col_exists(table, column):
            """Check if column exists in table"""
            try:
                cols = [c['name'] for c in inspector.get_columns(table)]
                return column in cols
            except:
                return False
        
        # Add to users table
        print("👤 Updating USERS table...")
        users_added = []
        
        if not col_exists('users', 'branch_access'):
            db.execute(text("ALTER TABLE users ADD COLUMN branch_access VARCHAR(10) DEFAULT 'cpns'"))
            users_added.append('branch_access')
        
        if not col_exists('users', 'session_count'):
            db.execute(text("ALTER TABLE users ADD COLUMN session_count INTEGER DEFAULT 0"))
            users_added.append('session_count')
        
        if users_added:
            db.commit()
            print(f"   ✅ Added: {', '.join(users_added)}")
        else:
            print("   ℹ️  All columns already exist")
        print()
        
        # Add to sessions table
        print("📝 Updating SESSIONS table...")
        exam_columns = {
            'is_exam_mode': 'BOOLEAN DEFAULT FALSE',
            'current_subject': 'VARCHAR(50)',
            'subject_order': 'JSONB',
            'time_per_subject': 'INTEGER DEFAULT 3600',
            'subject_times': 'JSONB'
        }
        
        sessions_added = []
        for col, typ in exam_columns.items():
            if not col_exists('question_sessions', col):
                db.execute(text(f"ALTER TABLE question_sessions ADD COLUMN {col} {typ}"))
                sessions_added.append(col)
        
        if sessions_added:
            db.commit()
            print(f"   ✅ Added: {', '.join(sessions_added)}")
        else:
            print("   ℹ️  All columns already exist")
        
        print()
        
        # ================================================================
        # PHASE 5: CREATE ADMIN USER
        # ================================================================
        
        print("=" * 70)
        print("👔 PHASE 5: CREATING ADMIN USER")
        print("=" * 70)
        print()
        
        from models import User
        from core.security import get_password_hash
        
        print("👤 Creating admin user with tier='admin'...")
        
        # Check if admin already exists (shouldn't, but just in case)
        existing_admin = db.query(User).filter(User.username == 'admin').first()
        
        if existing_admin:
            print("⚠️  Admin user already exists, updating...")
            existing_admin.tier = 'admin'
            existing_admin.role = 'admin'
            existing_admin.test_type = 'mixed'
            existing_admin.branch_access = 'both'
            existing_admin.session_count = 0
            existing_admin.is_active = True
            db.commit()
            db.refresh(existing_admin)
            admin = existing_admin
        else:
            # Create new admin
            admin = User(
                username='admin',
                hashed_password=get_password_hash('admin123'),
                full_name='System Administrator',
                role='admin',
                tier='admin',  # ADMIN TIER
                test_type='mixed',
                branch_access='both',  # Access to both CPNS & POLRI
                session_count=0,
                is_active=True
            )
            db.add(admin)
            db.commit()
            db.refresh(admin)
        
        print("✅ Admin user created!")
        print()
        
        # Update existing users (set branch_access based on test_type)
        print("🔄 Updating existing users...")
        db.execute(text("""
            UPDATE users 
            SET branch_access = COALESCE(test_type, 'cpns')
            WHERE branch_access IS NULL
        """))
        db.execute(text("""
            UPDATE users 
            SET branch_access = 'both' 
            WHERE tier IN ('admin', 'premium')
        """))
        db.commit()
        print("✅ Existing users updated")
        print()
        
        db.close()
        
        # ================================================================
        # PHASE 6: FINAL VERIFICATION
        # ================================================================
        
        print("=" * 70)
        print("🔍 FINAL VERIFICATION")
        print("=" * 70)
        print()
        
        db = SessionLocal()
        
        # Verify tables
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"✅ Total tables: {len(tables)}")
        print()
        
        # Verify users table columns
        user_cols = [c['name'] for c in inspector.get_columns('users')]
        print("✅ Users table key columns:")
        required_user_cols = ['username', 'tier', 'role', 'branch_access', 'session_count']
        for col in required_user_cols:
            status = "✅" if col in user_cols else "❌"
            print(f"   {status} {col}")
        print()
        
        # Verify sessions table columns
        session_cols = [c['name'] for c in inspector.get_columns('question_sessions')]
        print("✅ Sessions table key columns:")
        required_session_cols = ['session_id', 'is_exam_mode', 'current_subject', 'subject_order']
        for col in required_session_cols:
            status = "✅" if col in session_cols else "❌"
            print(f"   {status} {col}")
        print()
        
        # Verify admin user
        admin = db.query(User).filter(User.username == 'admin').first()
        if admin:
            print("✅ Admin User Details:")
            print(f"   User ID: {admin.user_id}")
            print(f"   Username: {admin.username}")
            print(f"   Full Name: {admin.full_name}")
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
        print("📊 Database Summary:")
        print(f"   Database: {target_db}")
        print(f"   Tables: {len(tables)}")
        print(f"   Host: {config['host']}:{config['port']}")
        print()
        print("🔐 Login Credentials:")
        print("   Username: admin")
        print("   Password: admin123")
        print("   Tier: admin (Full Access + User Management)")
        print()
        print("🚀 Next Steps:")
        print("   1. Start backend:")
        print("      uvicorn main:app --reload")
        print()
        print("   2. Access API:")
        print("      Backend: http://localhost:8000")
        print("      API Docs: http://localhost:8000/docs")
        print()
        print("   3. Test login:")
        print("      curl -X POST http://localhost:8000/auth/login \\")
        print('        -H "Content-Type: application/json" \\')
        print('        -d \'{"username":"admin","password":"admin123"}\'')
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
        print("💡 Troubleshooting:")
        print("   1. Check if PostgreSQL is running:")
        print("      sc query postgresql-x64-14")
        print()
        print("   2. Start PostgreSQL if not running:")
        print("      net start postgresql-x64-14")
        print()
        print("   3. Verify password in .env file:")
        print(f"      DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/{target_db}")
        print()
        print("   4. Check PostgreSQL logs for errors")
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
        
        print("💡 If error persists:")
        print("   1. Check models.py for syntax errors")
        print("   2. Ensure all dependencies are installed:")
        print("      pip install psycopg2-binary sqlalchemy python-dotenv")
        print("   3. Verify database.py and core/security.py exist")
        print()

if __name__ == "__main__":
    try:
        quick_fresh_setup()
    except KeyboardInterrupt:
        print("\n\n❌ Setup cancelled by user\n")
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}\n")
        import traceback
        traceback.print_exc()