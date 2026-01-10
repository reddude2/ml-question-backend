"""
Initialize Database - With Auto Cleanup
Handles existing tables and indexes
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from database import engine, SessionLocal
from sqlalchemy import text, inspect
import traceback

def drop_all_tables_and_indexes():
    """Drop all tables and indexes completely"""
    print("🗑️  Dropping all existing tables and indexes...")
    
    with engine.connect() as conn:
        # Drop all tables with CASCADE
        conn.execute(text("""
            DO $$ 
            DECLARE 
                r RECORD;
            BEGIN
                -- Drop all tables
                FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') 
                LOOP
                    EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(r.tablename) || ' CASCADE';
                END LOOP;
                
                -- Drop all sequences
                FOR r IN (SELECT sequence_name FROM information_schema.sequences WHERE sequence_schema = 'public')
                LOOP
                    EXECUTE 'DROP SEQUENCE IF EXISTS ' || quote_ident(r.sequence_name) || ' CASCADE';
                END LOOP;
            END $$;
        """))
        conn.commit()
    
    print("✅ All tables and indexes dropped")

def init_database():
    """Initialize database with all tables"""
    
    try:
        print("=" * 60)
        print("🗄️  INITIALIZING DATABASE")
        print("=" * 60)
        print()
        
        # Test connection
        print("🔌 Testing database connection...")
        with engine.connect() as conn:
            result = conn.execute(text("SELECT current_database()"))
            db_name = result.scalar()
            print(f"✅ Connected to: {db_name}")
        print()
        
        # Import Base
        print("📦 Importing models...")
        from models import Base
        print("✅ Models imported")
        print()
        
        # Check existing tables
        print("🔍 Checking existing tables...")
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        
        if existing_tables:
            print(f"⚠️  Found {len(existing_tables)} existing tables:")
            for table in existing_tables:
                print(f"   - {table}")
            print()
            print("Options:")
            print("   1. Drop all and recreate (RECOMMENDED)")
            print("   2. Try to keep existing (may cause errors)")
            print("   3. Cancel")
            print()
            
            choice = input("Enter choice (1/2/3): ").strip()
            
            if choice == "1":
                print()
                drop_all_tables_and_indexes()
                print()
            elif choice == "3":
                print("❌ Cancelled")
                return
            elif choice == "2":
                print("⚠️  Attempting to keep existing tables...")
                print()
        else:
            print("✅ No existing tables (fresh database)")
            print()
        
        # Create all tables
        print("📊 Creating tables from models...")
        try:
            Base.metadata.create_all(bind=engine)
            print("✅ Tables created!")
        except Exception as e:
            print(f"❌ Error creating tables: {e}")
            print()
            print("💡 Recommendation: Drop database and try again")
            print("   Run: psql -U postgres -c \"DROP DATABASE ml_question_system;\"")
            print("   Then: psql -U postgres -c \"CREATE DATABASE ml_question_system;\"")
            raise
        
        print()
        
        # Verify tables
        print("🔍 Verifying created tables...")
        inspector = inspect(engine)
        created_tables = inspector.get_table_names()
        
        print(f"✅ Database now has {len(created_tables)} tables:")
        for table in created_tables:
            columns = inspector.get_columns(table)
            print(f"   ✅ {table} ({len(columns)} columns)")
        print()
        
        # Create default admin
        print("👤 Creating default admin user...")
        
        from models import User
        from core.security import get_password_hash
        
        db = SessionLocal()
        
        try:
            admin = db.query(User).filter(User.username == 'admin').first()
            
            if not admin:
                admin = User(
                    username='admin',
                    hashed_password=get_password_hash('admin123'),
                    full_name='System Administrator',
                    role='admin',
                    tier='free',
                    test_type='mixed',
                    is_active=True
                )
                db.add(admin)
                db.commit()
                db.refresh(admin)
                
                print("✅ Admin user created!")
                print(f"   Username: admin")
                print(f"   Password: admin123")
            else:
                print("✅ Admin user already exists")
            
        except Exception as e:
            print(f"⚠️  Admin creation: {e}")
            db.rollback()
        finally:
            db.close()
        
        print()
        print("=" * 60)
        print("✅✅✅ DATABASE INITIALIZATION COMPLETE! ✅✅✅")
        print("=" * 60)
        print()
        print("📋 Tables created:")
        for table in created_tables:
            print(f"   ✅ {table}")
        print()
        print("🔄 NEXT STEPS:")
        print("   1. Run: python add_exam_mode_columns.py")
        print("   2. Run: python create_admin_tier.py")
        print("   3. Start: uvicorn main:app --reload")
        print()
        
    except Exception as e:
        print()
        print("=" * 60)
        print("❌ ERROR OCCURRED")
        print("=" * 60)
        print(f"Error: {e}")
        print()
        traceback.print_exc()
        print()

if __name__ == "__main__":
    init_database()