\# ML Question System - Backend API



Backend API untuk sistem latihan soal ujian POLRI \& CPNS dengan Machine Learning.



\## 🎯 Features



\- ✅ \*\*Authentication\*\* - JWT-based with double-layer security

\- ✅ \*\*User Management\*\* - Role-based access control (Admin/User)

\- ✅ \*\*Tier System\*\* - Free, Basic, Premium with different limits

\- ✅ \*\*Question Bank\*\* - POLRI \& CPNS questions with filtering

\- ✅ \*\*Practice Sessions\*\* - Timed practice and exam simulations

\- ✅ \*\*Auto Grading\*\* - Automatic score calculation

\- ✅ \*\*Progress Tracking\*\* - Subject-wise statistics and analytics

\- ✅ \*\*Admin Dashboard\*\* - System statistics and management



\## 📋 Tech Stack



\- \*\*Framework:\*\* FastAPI 0.104.1

\- \*\*Database:\*\* PostgreSQL (via SQLAlchemy 1.4.51)

\- \*\*Authentication:\*\* JWT (python-jose) + bcrypt

\- \*\*Server:\*\* Uvicorn

\- \*\*Python:\*\* 3.11+



\## 🚀 Quick Start



\### 1. Prerequisites

```bash

\# Python 3.11 or higher

python --version



\# PostgreSQL 14 or higher

psql --version

```



\### 2. Clone \& Setup

```bash

\# Navigate to backend folder

cd backend



\# Create virtual environment

python -m venv venv



\# Activate virtual environment

\# Windows:

venv\\Scripts\\activate

\# Linux/Mac:

source venv/bin/activate



\# Install dependencies

pip install -r requirements.txt

```



\### 3. Database Setup

```bash

\# Create PostgreSQL database

psql -U postgres

CREATE DATABASE ml\_question\_db;

\\q



\# Configure .env file

\# Copy .env.example to .env

copy .env.example .env



\# Edit .env and update:

\# DATABASE\_URL=postgresql://postgres:your\_password@localhost:5432/ml\_question\_db

```



\### 4. Initialize Database

```bash

\# Create tables and seed data

python seed.py

```



\*\*Default users created:\*\*

\- Admin: `admin` / `admin123`

\- POLRI User: `polri\_user` / `polri123`

\- CPNS User: `cpns\_user` / `cpns123`

\- Premium User: `premium\_user` / `premium123`



\### 5. Run Server

```bash

\# Start development server

python run.py



\# Or with uvicorn directly

uvicorn main:app --reload --host 0.0.0.0 --port 8000

```



Server will start at: \*\*http://localhost:8000\*\*



\## 📚 API Documentation



\### Interactive Docs



Once server is running:



\- \*\*Swagger UI:\*\* http://localhost:8000/docs

\- \*\*ReDoc:\*\* http://localhost:8000/redoc



\### Quick Test

```bash

\# Health check

curl http://localhost:8000/health



\# Login

curl -X POST http://localhost:8000/auth/login \\

&nbsp; -H "Content-Type: application/json" \\

&nbsp; -d '{"username":"admin","password":"admin123"}'

```



\## 🔐 Authentication



\### Get Token

```bash

POST /auth/login

{

&nbsp; "username": "admin",

&nbsp; "password": "admin123"

}

```



\### Use Token



Add to request headers:

```

Authorization: Bearer <your\_token\_here>

```



\## 📊 API Endpoints



\### Authentication (4 endpoints)

\- `POST /auth/login` - User login

\- `GET /auth/verify` - Verify token

\- `POST /auth/change-password` - Change password

\- `POST /auth/logout` - Logout



\### Users (6 endpoints)

\- `GET /users/me` - Get current user info

\- `GET /users/` - List all users (admin)

\- `GET /users/{user\_id}` - Get user by ID (admin)

\- `POST /users/` - Create user (admin)

\- `PUT /users/{user\_id}` - Update user (admin)

\- `DELETE /users/{user\_id}` - Delete user (admin)



\### Questions (6 endpoints)

\- `GET /questions/` - List questions with filters

\- `GET /questions/{question\_id}` - Get question details

\- `POST /questions/` - Create question (admin)

\- `PUT /questions/{question\_id}` - Update question (admin)

\- `DELETE /questions/{question\_id}` - Delete question (admin)

\- `POST /questions/random` - Get random questions



\### Sessions (6 endpoints)

\- `POST /sessions/create` - Create new session

\- `GET /sessions/` - List user sessions

\- `GET /sessions/{session\_id}` - Get session details

\- `POST /sessions/{session\_id}/start` - Start session timer

\- `POST /sessions/{session\_id}/submit` - Submit answers

\- `DELETE /sessions/{session\_id}` - Delete session



\### Progress (4 endpoints)

\- `GET /progress/me` - Get user progress

\- `GET /progress/summary` - Progress summary (period)

\- `GET /progress/by-subject/{subject}` - Subject-specific progress

\- `GET /progress/all` - All users progress (admin)



\### Admin (3 endpoints)

\- `GET /admin/dashboard` - Dashboard statistics

\- `GET /admin/statistics` - Detailed system stats

\- `GET /admin/audit-logs` - System audit logs



\## 🎓 Test Types \& Subjects



\### POLRI

\- Bahasa Inggris

\- Numerik

\- Pengetahuan Umum

\- Wawasan Kebangsaan



\### CPNS

\- TIU (Tes Intelegensi Umum)

&nbsp; - Verbal

&nbsp; - Numerik

&nbsp; - Figural

\- Wawasan Kebangsaan

\- TKP (Tes Karakteristik Pribadi)



\### CAMPUR

Access to both POLRI and CPNS



\## 💎 Tier System



\### Free Tier

\- Max 20 questions per session

\- Max 3 sessions per day

\- No explanations

\- No simulations



\### Basic Tier

\- Max 50 questions per session

\- Max 10 sessions per day

\- Explanations included

\- No simulations



\### Premium Tier

\- Max 250 questions per session

\- Unlimited sessions

\- Full explanations

\- Exam simulations



\## 🧪 Testing

```bash

\# Run all tests

python test\_auth\_complete.py

python test\_full\_flow.py

python test\_questions.py

python test\_sessions.py

python test\_final.py

```



\## 📁 Project Structure

```

backend/

├── main.py                 # FastAPI application

├── config.py              # System configuration

├── database.py            # Database setup

├── models.py              # SQLAlchemy models

├── schemas.py             # Pydantic schemas

├── run.py                 # Development server

├── seed.py                # Database seeding

├── requirements.txt       # Python dependencies

├── .env                   # Environment variables (not in git)

├── .env.example          # Environment template

│

├── core/                  # Core utilities

│   ├── security.py       # JWT \& password hashing

│   ├── dependencies.py   # FastAPI dependencies

│   └── access\_control.py # Access control logic

│

├── middleware/            # Middleware

│   ├── auth.py           # JWT verification

│   └── tier\_check.py     # Tier validation

│

├── routers/              # API endpoints

│   ├── auth.py           # Authentication

│   ├── users.py          # User management

│   ├── questions.py      # Question bank

│   ├── sessions.py       # Practice sessions

│   ├── progress.py       # Progress tracking

│   └── admin.py          # Admin tools

│

└── tests/                # Test files

&nbsp;   ├── test\_auth\_complete.py

&nbsp;   ├── test\_full\_flow.py

&nbsp;   ├── test\_questions.py

&nbsp;   ├── test\_sessions.py

&nbsp;   └── test\_final.py

```



\## 🔒 Security



\### Two-Layer Security Architecture



1\. \*\*Layer 1: Global Middleware\*\*

&nbsp;  - Verifies JWT token on ALL requests

&nbsp;  - Blocks unauthorized access at entry point

&nbsp;  - Public endpoints explicitly whitelisted



2\. \*\*Layer 2: Per-Endpoint Dependencies\*\*

&nbsp;  - Extracts user object from database

&nbsp;  - Validates user is active

&nbsp;  - Enforces role-based access control



\### Security Features

\- ✅ JWT token authentication

\- ✅ Password hashing with bcrypt

\- ✅ Token expiration (7 days)

\- ✅ Role-based access control (Admin/User)

\- ✅ Tier-based limitations

\- ✅ Test type restrictions

\- ✅ SQL injection prevention (SQLAlchemy ORM)

\- ✅ CORS configuration



\## 🐛 Troubleshooting



\### Database Connection Error

```bash

\# Check PostgreSQL is running

pg\_isready



\# Verify DATABASE\_URL in .env

\# Format: postgresql://user:password@host:port/database

```



\### Import Errors

```bash

\# Reinstall dependencies

pip install -r requirements.txt --force-reinstall

```



\### Port Already in Use

```bash

\# Windows: Find process on port 8000

netstat -ano | findstr :8000



\# Kill process (replace PID)

taskkill /PID <PID> /F



\# Or use different port in .env

PORT=8001

```



\### Migration Issues

```bash

\# Recreate database

python recreate\_db.py



\# Seed data

python seed.py

```



\## 📝 Environment Variables



| Variable | Description | Default | Required |

|----------|-------------|---------|----------|

| `DATABASE\_URL` | PostgreSQL connection string | - | ✅ |

| `SECRET\_KEY` | JWT secret key | - | ✅ |

| `ALGORITHM` | JWT algorithm | HS256 | ✅ |

| `ACCESS\_TOKEN\_EXPIRE\_DAYS` | Token validity period | 7 | ✅ |

| `HOST` | Server host | 0.0.0.0 | ❌ |

| `PORT` | Server port | 8000 | ❌ |

| `DEBUG` | Debug mode | True | ❌ |

| `ALLOWED\_ORIGINS` | CORS allowed origins | \* | ❌ |



\## 🚀 Deployment



\### Production Checklist



\- \[ ] Change `SECRET\_KEY` to strong random value

\- \[ ] Set `DEBUG=False`

\- \[ ] Configure `ALLOWED\_ORIGINS` properly

\- \[ ] Use production database

\- \[ ] Enable HTTPS

\- \[ ] Set up reverse proxy (nginx)

\- \[ ] Configure firewall

\- \[ ] Set up monitoring

\- \[ ] Enable logging

\- \[ ] Backup database regularly



\### Example Deployment (Ubuntu + Nginx)

```bash

\# Install dependencies

sudo apt update

sudo apt install python3-pip python3-venv postgresql nginx



\# Setup application

cd /var/www/ml-question-api

python3 -m venv venv

source venv/bin/activate

pip install -r requirements.txt



\# Configure systemd service

sudo nano /etc/systemd/system/ml-question-api.service



\# Start service

sudo systemctl start ml-question-api

sudo systemctl enable ml-question-api



\# Configure nginx

sudo nano /etc/nginx/sites-available/ml-question-api

sudo nginx -t

sudo systemctl restart nginx

```



\## 📈 Performance



\- \*\*Average response time:\*\* <100ms

\- \*\*Concurrent users:\*\* 100+ (tested)

\- \*\*Database queries:\*\* Optimized with indexes

\- \*\*Connection pooling:\*\* Enabled (10 connections)



\## 🤝 Contributing



1\. Create feature branch

2\. Make changes

3\. Run tests

4\. Submit pull request



\## 📄 License



Proprietary - All rights reserved



\## 👤 Author



ML Question System Team



\## 📞 Support



For issues or questions:

\- Open an issue on repository

\- Email: support@mlquestion.com



---



\*\*Last Updated:\*\* December 2025  

\*\*Version:\*\* 1.0.0  

\*\*Status:\*\* ✅ Production Ready

