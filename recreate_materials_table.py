"""
Recreate materials table with new structure
WARNING: This will DELETE all existing materials!
"""

from database import engine
from sqlalchemy import text

def recreate_materials_table():
    """Drop and recreate materials table"""
    
    print("=" * 70)
    print("⚠️  RECREATING MATERIALS TABLE")
    print("=" * 70)
    print()
    
    # Use begin() for automatic transaction management
    with engine.begin() as conn:
        # Drop old table
        print("1. Dropping old materials table...")
        try:
            conn.execute(text("DROP TABLE IF EXISTS materials CASCADE"))
            print("   ✅ Dropped")
        except Exception as e:
            print(f"   ⚠️  Warning: {e}")
        
        # Create new table
        print("\n2. Creating new materials table...")
        conn.execute(text("""
            CREATE TABLE materials (
                material_id VARCHAR(50) PRIMARY KEY,
                test_category VARCHAR(20) NOT NULL,
                subject VARCHAR(50) NOT NULL,
                topic VARCHAR(200) NOT NULL,
                content TEXT NOT NULL,
                difficulty VARCHAR(20) DEFAULT 'sedang' NOT NULL,
                tags VARCHAR(50)[],
                examples TEXT[],
                extra_data JSONB,
                is_active BOOLEAN DEFAULT true NOT NULL,
                question_count INTEGER DEFAULT 0 NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
                CONSTRAINT check_material_category CHECK (test_category IN ('cpns', 'polri')),
                CONSTRAINT check_material_difficulty CHECK (difficulty IN ('mudah', 'sedang', 'sulit'))
            )
        """))
        print("   ✅ Created")
        
        # Create indexes
        print("\n3. Creating indexes...")
        conn.execute(text("CREATE INDEX idx_materials_category_subject ON materials(test_category, subject)"))
        conn.execute(text("CREATE INDEX idx_materials_active ON materials(is_active)"))
        print("   ✅ Indexes created")
        
        # Update questions table
        print("\n4. Updating questions table...")
        
        # Drop old FK constraint if exists
        try:
            conn.execute(text("""
                ALTER TABLE questions 
                DROP CONSTRAINT IF EXISTS questions_material_id_fkey
            """))
        except Exception as e:
            print(f"   ⚠️  Note: {e}")
        
        # Rename column if exists
        try:
            conn.execute(text("""
                ALTER TABLE questions 
                RENAME COLUMN material_id TO source_material_id
            """))
            print("   ✅ Renamed material_id to source_material_id")
        except Exception as e:
            print(f"   ℹ️  Column already renamed or doesn't exist: {e}")
        
        # Add new FK constraint
        try:
            conn.execute(text("""
                ALTER TABLE questions 
                ADD CONSTRAINT questions_source_material_id_fkey 
                FOREIGN KEY (source_material_id) 
                REFERENCES materials(material_id) 
                ON DELETE SET NULL
            """))
            print("   ✅ Added FK constraint")
        except Exception as e:
            print(f"   ⚠️  FK constraint: {e}")
        
        # Add new question columns if not exists
        print("\n5. Adding new columns to questions table...")
        
        columns_to_add = [
            ("option_a", "TEXT"),
            ("option_b", "TEXT"),
            ("option_c", "TEXT"),
            ("option_d", "TEXT"),
            ("option_e", "TEXT"),
            ("tags", "VARCHAR(50)[]"),
        ]
        
        for col_name, col_type in columns_to_add:
            try:
                conn.execute(text(f"""
                    ALTER TABLE questions 
                    ADD COLUMN IF NOT EXISTS {col_name} {col_type}
                """))
                print(f"   ✅ Added column: {col_name}")
            except Exception as e:
                print(f"   ℹ️  Column {col_name}: {e}")
        
    print("\n" + "=" * 70)
    print("✅ MATERIALS TABLE RECREATED SUCCESSFULLY!")
    print("=" * 70)
    print()
    print("Next steps:")
    print("1. Restart backend: python main.py")
    print("2. Test materials endpoint: http://localhost:8000/materials")
    print("3. Open material input form: admin_panel/material-input.html")
    print()

if __name__ == "__main__":
    try:
        recreate_materials_table()
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()