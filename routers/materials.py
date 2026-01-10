"""
Materials Router
CRUD operations for learning materials
FINAL FIX - Language Detection + Reading Passages + Duplicate Handling
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from uuid import uuid4
import os
import json
import re
import requests
import time
import traceback

from database import get_db
from models import Material, Question
from pydantic import BaseModel

router = APIRouter(prefix="/materials", tags=["Materials"])

# ============================================================================
# CONFIGURATION FROM .ENV
# ============================================================================

def get_gemini_config():
    """Load Gemini configuration from environment variables"""
    models_raw = os.getenv('GEMINI_MODELS', 'gemini-2.5-flash,gemini-pro')
    
    raw_key = os.getenv('GEMINI_API_KEY', '')
    clean_key = raw_key.strip().replace('"', '').replace("'", "")
    
    return {
        'api_key': clean_key,
        'api_version': os.getenv('GEMINI_API_VERSION', 'v1'),
        'base_url': os.getenv('GEMINI_BASE_URL', 'https://generativelanguage.googleapis.com'),
        'models': [m.strip() for m in models_raw.split(',') if m.strip()],
        'default_model': os.getenv('GEMINI_DEFAULT_MODEL', 'gemini-2.5-flash'),
        'max_tokens': int(os.getenv('GEMINI_MAX_TOKENS', '8192')),
        'temperature': float(os.getenv('GEMINI_TEMPERATURE', '0.7')),
        'max_retries': int(os.getenv('GEMINI_MAX_RETRIES', '2')),
        'retry_delay': int(os.getenv('GEMINI_RETRY_DELAY', '10')),
        'timeout': int(os.getenv('GEMINI_REQUEST_TIMEOUT', '120')),
        'min_ratio': float(os.getenv('GEMINI_MIN_QUESTIONS_RATIO', '0.8')),
    }

def get_validation_config():
    """Load validation configuration from environment variables"""
    return {
        'validate_length': os.getenv('VALIDATE_QUESTION_LENGTH', 'true').lower() == 'true',
        'min_question': int(os.getenv('MIN_QUESTION_LENGTH', '10')),
        'max_question': int(os.getenv('MAX_QUESTION_LENGTH', '500')),
        'min_option': int(os.getenv('MIN_OPTION_LENGTH', '1')),
        'max_option': int(os.getenv('MAX_OPTION_LENGTH', '200')),
        'validate_explanation': os.getenv('VALIDATE_EXPLANATION', 'true').lower() == 'true',
        'min_explanation': int(os.getenv('MIN_EXPLANATION_LENGTH', '20')),
    }

def get_defaults():
    """Load default values from environment variables"""
    return {
        'num_questions': int(os.getenv('DEFAULT_NUM_QUESTIONS', '10')),
        'difficulty': os.getenv('DEFAULT_DIFFICULTY', 'sedang'),
        'language': os.getenv('DEFAULT_LANGUAGE', 'Indonesian'),
    }

# ============================================================================
# SCHEMAS
# ============================================================================

class MaterialCreate(BaseModel):
    test_category: str
    subject: str
    topic: str
    content: str
    difficulty: str = "sedang"
    tags: Optional[List[str]] = []
    examples: Optional[List[str]] = None

class MaterialUpdate(BaseModel):
    test_category: Optional[str] = None
    subject: Optional[str] = None
    topic: Optional[str] = None
    content: Optional[str] = None
    difficulty: Optional[str] = None
    tags: Optional[List[str]] = None
    examples: Optional[List[str]] = None
    is_active: Optional[bool] = None

class MaterialResponse(BaseModel):
    material_id: str
    test_category: str
    subject: str
    topic: str
    content: str
    difficulty: str
    tags: Optional[List[str]] = None
    examples: Optional[List[str]] = None
    is_active: bool
    question_count: int = 0
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

class GenerateQuestionsRequest(BaseModel):
    num_questions: int = 5

# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("", response_model=MaterialResponse, status_code=status.HTTP_201_CREATED)
def create_material(material_data: MaterialCreate, db: Session = Depends(get_db)):
    """Create new learning material - PUBLIC"""
    
    print(f"\n{'='*70}")
    print(f"📚 CREATING MATERIAL")
    print(f"{'='*70}")
    print(f"Topic: {material_data.topic}")
    print(f"Category: {material_data.test_category}")
    print(f"Subject: {material_data.subject}")
    print(f"{'='*70}\n")
    
    try:
        material = Material(
            material_id=str(uuid4()),
            test_category=material_data.test_category,
            subject=material_data.subject,
            topic=material_data.topic,
            content=material_data.content,
            difficulty=material_data.difficulty,
            tags=material_data.tags if material_data.tags else [],
            examples=material_data.examples,
            extra_data=None,
            is_active=True,
            question_count=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.add(material)
        db.commit()
        db.refresh(material)
        
        print(f"✅ Material created: {material.material_id}\n")
        
        return {
            "material_id": material.material_id,
            "test_category": material.test_category,
            "subject": material.subject,
            "topic": material.topic,
            "content": material.content,
            "difficulty": material.difficulty,
            "tags": material.tags or [],
            "examples": material.examples,
            "is_active": material.is_active,
            "question_count": material.question_count or 0,
            "created_at": material.created_at,
            "updated_at": material.updated_at
        }
        
    except Exception as e:
        print(f"❌ Error: {e}")
        traceback.print_exc()
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create material: {str(e)}")

@router.get("", response_model=List[MaterialResponse])
def get_materials(test_category: Optional[str] = None, subject: Optional[str] = None, 
                  difficulty: Optional[str] = None, limit: int = 100, db: Session = Depends(get_db)):
    """Get all materials with filters - PUBLIC"""
    
    query = db.query(Material).filter(Material.is_active == True)
    
    if test_category:
        query = query.filter(Material.test_category == test_category)
    if subject:
        query = query.filter(Material.subject == subject)
    if difficulty:
        query = query.filter(Material.difficulty == difficulty)
    
    materials = query.order_by(Material.created_at.desc()).limit(limit).all()
    print(f"📚 Retrieved {len(materials)} materials")
    
    return [
        {
            "material_id": m.material_id,
            "test_category": m.test_category,
            "subject": m.subject,
            "topic": m.topic,
            "content": m.content,
            "difficulty": m.difficulty,
            "tags": m.tags or [],
            "examples": m.examples,
            "is_active": m.is_active,
            "question_count": m.question_count or 0,
            "created_at": m.created_at,
            "updated_at": m.updated_at
        }
        for m in materials
    ]

@router.get("/stats/overview")
def get_materials_stats(db: Session = Depends(get_db)):
    """Get materials statistics - PUBLIC"""
    
    from sqlalchemy import func
    
    total_materials = db.query(func.count(Material.material_id)).filter(Material.is_active == True).scalar()
    total_questions = db.query(func.count(Question.question_id)).scalar()
    
    by_category = db.query(Material.test_category, func.count(Material.material_id).label('count')).filter(
        Material.is_active == True).group_by(Material.test_category).all()
    
    by_subject = db.query(Material.subject, func.count(Material.material_id).label('count')).filter(
        Material.is_active == True).group_by(Material.subject).all()
    
    return {
        "total_materials": total_materials or 0,
        "total_questions": total_questions or 0,
        "by_category": [{"category": cat, "count": count} for cat, count in by_category],
        "by_subject": [{"subject": subj, "count": count} for subj, count in by_subject]
    }

@router.get("/{material_id}", response_model=MaterialResponse)
def get_material(material_id: str, db: Session = Depends(get_db)):
    """Get single material by ID - PUBLIC"""
    
    material = db.query(Material).filter(Material.material_id == material_id, Material.is_active == True).first()
    
    if not material:
        raise HTTPException(status_code=404, detail=f"Material {material_id} not found")
    
    return {
        "material_id": material.material_id,
        "test_category": material.test_category,
        "subject": material.subject,
        "topic": material.topic,
        "content": material.content,
        "difficulty": material.difficulty,
        "tags": material.tags or [],
        "examples": material.examples,
        "is_active": material.is_active,
        "question_count": material.question_count or 0,
        "created_at": material.created_at,
        "updated_at": material.updated_at
    }

@router.put("/{material_id}", response_model=MaterialResponse)
def update_material(material_id: str, material_update: MaterialUpdate, db: Session = Depends(get_db)):
    """Update material details - PUBLIC"""
    
    material = db.query(Material).filter(Material.material_id == material_id, Material.is_active == True).first()
    if not material:
        raise HTTPException(status_code=404, detail=f"Material {material_id} not found")
    
    try:
        if material_update.test_category: material.test_category = material_update.test_category
        if material_update.subject: material.subject = material_update.subject
        if material_update.topic: material.topic = material_update.topic
        if material_update.content: material.content = material_update.content
        if material_update.difficulty: material.difficulty = material_update.difficulty
        if material_update.tags: material.tags = material_update.tags
        if material_update.examples: material.examples = material_update.examples
        if material_update.is_active is not None: material.is_active = material_update.is_active
        
        material.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(material)
        
        return {
            "material_id": material.material_id,
            "test_category": material.test_category,
            "subject": material.subject,
            "topic": material.topic,
            "content": material.content,
            "difficulty": material.difficulty,
            "tags": material.tags or [],
            "examples": material.examples,
            "is_active": material.is_active,
            "question_count": material.question_count or 0,
            "created_at": material.created_at,
            "updated_at": material.updated_at
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update: {str(e)}")

@router.post("/{material_id}/generate")
def generate_questions_from_material(material_id: str, request: GenerateQuestionsRequest, db: Session = Depends(get_db)):
    """Generate questions using Gemini AI - WITH READING PASSAGE & DUPLICATE HANDLING"""
    
    material = db.query(Material).filter(Material.material_id == material_id, Material.is_active == True).first()
    if not material:
        raise HTTPException(status_code=404, detail=f"Material not found")
    
    config = get_gemini_config()
    validation = get_validation_config()
    defaults = get_defaults()
    
    # ✅ DETECT LANGUAGE FROM SUBJECT
    language = "English" if material.subject.lower() == "bahasa_inggris" else "Indonesian"
    
    # ✅ DETECT IF READING COMPREHENSION
    is_reading = "reading" in material.topic.lower() or "comprehension" in material.topic.lower()
    
    print(f"\n{'='*70}")
    print(f"🤖 GENERATING QUESTIONS")
    print(f"{'='*70}")
    print(f"Material: {material.topic}")
    print(f"Subject: {material.subject}")
    print(f"Language: {language}")
    print(f"Reading: {'Yes' if is_reading else 'No'}")
    print(f"Questions: {request.num_questions}")
    print(f"Models: {', '.join(config['models'])}")
    print(f"{'='*70}\n")
    
    try:
        api_key = config['api_key']
        if not api_key:
            raise HTTPException(status_code=500, detail="GEMINI_API_KEY not configured")
        
        # ✅ CREATE PROMPT BASED ON TYPE
        if is_reading:
            prompt = f"""Generate {request.num_questions} reading comprehension questions in {language}.

STEP 1: Create a SHORT reading passage (120-180 words) in {language} about: {material.topic}

STEP 2: Create {request.num_questions} questions based on that passage.

Guidelines:
{material.content}

CRITICAL: Output ONLY valid JSON. NO markdown, NO backticks, NO extra text.

Format (all questions use SAME reading_passage):
[
  {{
    "reading_passage": "Complete reading text here in {language}...",
    "question_text": "Question 1?",
    "option_a": "A",
    "option_b": "B",
    "option_c": "C",
    "option_d": "D",
    "option_e": "E",
    "correct_answer": "A",
    "explanation": "Explanation"
  }},
  {{
    "reading_passage": "SAME reading text here...",
    "question_text": "Question 2?",
    ...
  }}
]

Output JSON now:"""
        else:
            prompt = f"""Generate {request.num_questions} multiple-choice questions in {language}.

Topic: {material.topic}
Subject: {material.subject}
Difficulty: {material.difficulty}

Guidelines:
{material.content}

CRITICAL: Output ONLY valid JSON. NO markdown, NO backticks, NO extra text.

Format:
[
  {{
    "question_text": "Question?",
    "option_a": "A",
    "option_b": "B",
    "option_c": "C",
    "option_d": "D",
    "option_e": "E",
    "correct_answer": "A",
    "explanation": "Explanation"
  }}
]

Output JSON now:"""
        
        text = None
        working_model = None
        
        for model_name in config['models']:
            try:
                print(f"   🔄 Trying: {model_name}")
                
                full_url = f"{config['base_url']}/{config['api_version']}/models/{model_name.strip()}:generateContent?key={api_key}"
                
                response = requests.post(
                    full_url,
                    headers={'Content-Type': 'application/json'},
                    json={
                        'contents': [{'parts': [{'text': prompt}]}],
                        'generationConfig': {
                            'temperature': config['temperature'],
                            'maxOutputTokens': 8192,
                        }
                    },
                    timeout=config['timeout']
                )
                
                print(f"      Status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    if 'candidates' in data and len(data['candidates']) > 0:
                        candidate = data['candidates'][0]
                        if 'content' in candidate and 'parts' in candidate['content']:
                            text = candidate['content']['parts'][0]['text']
                            working_model = model_name
                            print(f"   ✅ SUCCESS with: {working_model}")
                            break
                elif response.status_code == 429:
                    print(f"      ⚠️ Quota exceeded")
                    continue
                    
            except Exception as e:
                print(f"      ❌ Error: {str(e)[:50]}")
                continue
        
        if not text:
            raise HTTPException(status_code=500, detail="All models failed")
        
        print(f"📥 Received response from Gemini AI")
        print(f"📏 Response length: {len(text)} chars")
        
        # ✅ AGGRESSIVE JSON CLEANING
        text = text.strip()
        text = re.sub(r'```json\s*', '', text, flags=re.IGNORECASE)
        text = re.sub(r'```\s*', '', text, flags=re.IGNORECASE)
        
        if '[' in text:
            text = text[text.find('['):]
        if ']' in text:
            text = text[:text.rfind(']')+1]
        
        text = text.strip()
        
        print(f"🔍 Cleaned: {len(text)} chars")
        
        # ✅ PARSE JSON WITH SALVAGE
        try:
            questions_data = json.loads(text)
            print(f"✅ Parsed {len(questions_data)} questions")
        except json.JSONDecodeError as je:
            print(f"❌ JSON Error: {je}")
            
            # Try to salvage partial JSON
            try:
                last_complete = text.rfind('}')
                if last_complete > 0:
                    salvaged = text[:last_complete+1] + ']'
                    questions_data = json.loads(salvaged)
                    print(f"⚠️ Salvaged {len(questions_data)} questions")
                else:
                    raise HTTPException(status_code=500, detail="Invalid JSON - cannot salvage")
            except:
                print(f"❌ Full response: {text[:1000]}...")
                raise HTTPException(status_code=500, detail=f"Invalid JSON: {str(je)}")
        
        # ✅ SAVE TO DATABASE WITH READING_PASSAGE
        created_questions = []
        reading_passage = None
        
        for i, qdata in enumerate(questions_data, 1):
            # Extract reading passage if present
            if 'reading_passage' in qdata and not reading_passage:
                reading_passage = qdata['reading_passage']
                print(f"📖 Reading passage ({len(reading_passage)} chars): {reading_passage[:80]}...")
            
            required = ['question_text', 'option_a', 'option_b', 'option_c', 'option_d', 'option_e', 'correct_answer']
            if any(f not in qdata for f in required):
                print(f"   ⚠️ Q{i} missing fields")
                continue
            
            question = Question(
                question_id=str(uuid4()),
                test_category=material.test_category,
                subject=material.subject,
                difficulty=material.difficulty,
                reading_passage=reading_passage,  # ✅ SAVE READING PASSAGE HERE!
                question_text=qdata['question_text'],
                option_a=qdata['option_a'],
                option_b=qdata['option_b'],
                option_c=qdata['option_c'],
                option_d=qdata['option_d'],
                option_e=qdata['option_e'],
                correct_answer=qdata['correct_answer'],
                explanation=qdata.get('explanation', ''),
                tags=material.tags,
                source_material_id=material.material_id,
                created_at=datetime.utcnow()
            )
            
            db.add(question)
            created_questions.append(question)
            print(f"   {i}. [{language[:2].upper()}] {qdata['question_text'][:60]}...")
        
        if not created_questions:
            raise HTTPException(status_code=500, detail="No valid questions")
        
        # ✅ HANDLE DUPLICATES GRACEFULLY
        try:
            db.commit()
            saved_count = len(created_questions)
        except Exception as e:
            db.rollback()
            error_msg = str(e)
            if "duplicate key" in error_msg.lower() or "uniqueviolation" in error_msg.lower():
                print(f"⚠️ Warning: Some questions already exist")
                # Save one by one, skip duplicates
                saved_count = 0
                saved_questions = []
                for q in created_questions:
                    try:
                        db.add(q)
                        db.commit()
                        saved_count += 1
                        saved_questions.append(q)
                    except Exception:
                        db.rollback()
                        print(f"   ⚠️ Skipped duplicate: {q.question_text[:50]}...")
                        continue
                
                created_questions = saved_questions
                
                if saved_count == 0:
                    raise HTTPException(status_code=409, detail="All questions already exist in database")
                
                print(f"   ✅ Saved {saved_count} new questions (skipped duplicates)")
            else:
                raise
        
        # Update material
        material.question_count = (material.question_count or 0) + len(created_questions)
        material.updated_at = datetime.utcnow()
        db.commit()
        
        print(f"\n✅ Saved {len(created_questions)} questions")
        print(f"   Language: {language}")
        print(f"   Model: {working_model}")
        if reading_passage:
            print(f"   Reading: {len(reading_passage)} chars")
        print(f"{'='*70}\n")
        
        return {
            "status": "success",
            "material_id": material_id,
            "count": len(created_questions),
            "model_used": working_model,
            "language": language,
            "has_reading": reading_passage is not None,
            "message": f"Generated {len(created_questions)} {language} questions"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error: {e}")
        traceback.print_exc()
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{material_id}")
def delete_material(material_id: str, db: Session = Depends(get_db)):
    """Soft delete material - PUBLIC"""
    
    material = db.query(Material).filter(Material.material_id == material_id).first()
    if not material:
        raise HTTPException(status_code=404, detail=f"Material not found")
    
    material.is_active = False
    material.updated_at = datetime.utcnow()
    db.commit()
    
    print(f"🗑️ Deleted: {material_id}")
    return {"status": "success", "message": "Material deleted"}