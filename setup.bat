@echo off
cls
echo ============================================================
echo 🚀 COMPLETE DATABASE SETUP
echo ============================================================
echo.

echo 🗑️  Step 1: Dropping old database...
psql -U postgres -d postgres -c "DROP DATABASE IF EXISTS ml_question_system;"
if %errorlevel% neq 0 (
    echo ❌ Failed - Check if PostgreSQL is running
    echo    Start it with: net start postgresql-x64-14
    pause
    exit /b 1
)
echo ✅ Database dropped
echo.

echo 📦 Step 2: Creating fresh database...
psql -U postgres -d postgres -c "CREATE DATABASE ml_question_system;"
if %errorlevel% neq 0 (
    echo ❌ Failed to create database
    pause
    exit /b 1
)
echo ✅ Database created
echo.

echo 📊 Step 3: Creating tables...
python init_db.py
if %errorlevel% neq 0 (
    echo ❌ Failed to create tables
    pause
    exit /b 1
)

echo 📝 Step 4: Adding exam columns...
python add_exam_mode_columns.py
if %errorlevel% neq 0 (
    echo ❌ Failed to add columns
    pause
    exit /b 1
)

echo 👔 Step 5: Creating admin user...
python create_admin_tier.py
if %errorlevel% neq 0 (
    echo ❌ Failed to create admin
    pause
    exit /b 1
)

echo.
echo ============================================================
echo ✅✅✅ SETUP COMPLETE! ✅✅✅
echo ============================================================
echo.
echo 🔐 Login Credentials:
echo    Username: admin
echo    Password: admin123
echo    Tier: admin (Full Access)
echo.
echo 🚀 Next Step:
echo    uvicorn main:app --reload
echo.
echo ============================================================
echo.
pause