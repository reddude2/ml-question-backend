"""
Add balanced test questions
Ensures equal distribution across difficulties
"""
from database import SessionLocal
from models import Question
import secrets
import hashlib

db = SessionLocal()

def create_hash(text, answer):
    content = f"{text}|{answer}"
    return hashlib.sha256(content.encode()).hexdigest()

print("\n🔨 Adding balanced test questions...\n")

# Add 30 questions per difficulty = 90 total
difficulties = ['mudah', 'sedang', 'sulit']
questions_per_difficulty = 30

total_added = 0

for difficulty in difficulties:
    print(f"📚 Adding {questions_per_difficulty} {difficulty} questions...")
    
    for i in range(questions_per_difficulty):
        q_text = f"Soal TIU {difficulty} #{i+1}: Apa jawaban yang tepat?"
        
        question = Question(
            question_id=f"q_bal_{difficulty}_{secrets.token_hex(4)}",
            test_category='cpns',
            subject='tiu',
            subtype='verbal',
            difficulty=difficulty,
            question_text=q_text,
            options={
                'A': f'Pilihan A untuk soal {difficulty}',
                'B': f'Pilihan B untuk soal {difficulty}',
                'C': f'Pilihan C untuk soal {difficulty}',
                'D': f'Pilihan D untuk soal {difficulty}',
                'E': f'Pilihan E untuk soal {difficulty}'
            },
            correct_answer='A',
            explanation=f'Ini adalah penjelasan untuk soal {difficulty}.',
            content_hash=create_hash(q_text, 'A'),
            quality_score=0.85
        )
        
        db.add(question)
        total_added += 1
    
    db.commit()
    print(f"   ✅ Added {questions_per_difficulty} {difficulty} questions\n")

db.close()

print("=" * 60)
print(f"✅ Added {total_added} balanced questions!")
print("=" * 60)
print("\nDistribution:")
print("  • Mudah: 30 questions")
print("  • Sedang: 30 questions")
print("  • Sulit: 30 questions")
print("\nYou can now create sessions with 50+ questions!")
print("=" * 60 + "\n")