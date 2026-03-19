"""
Add test questions for session testing
Adds 60 questions: 20 TIU, 20 TWK, 20 TKP
"""
from database import SessionLocal
from models import Question
import secrets
import hashlib

db = SessionLocal()

def create_hash(text, answer):
    """Generate content hash"""
    content = f"{text}|{answer}"
    return hashlib.sha256(content.encode()).hexdigest()

print("\n🔨 Adding test questions...\n")

# Test questions data
test_questions = [
    # TIU - Verbal (20 questions)
    {
        'subject': 'tiu',
        'subtype': 'verbal',
        'questions': [
            ('Sinonim dari kata "senang" adalah...', 
             {'A': 'Gembira', 'B': 'Sedih', 'C': 'Marah', 'D': 'Takut', 'E': 'Bingung'}, 
             'A', 'Senang dan gembira memiliki makna yang sama.'),
            ('Antonim dari kata "besar" adalah...', 
             {'A': 'Luas', 'B': 'Tinggi', 'C': 'Kecil', 'D': 'Panjang', 'E': 'Berat'}, 
             'C', 'Besar berlawanan dengan kecil.'),
            ('Sinonim dari kata "indah" adalah...', 
             {'A': 'Cantik', 'B': 'Jelek', 'C': 'Buruk', 'D': 'Kotor', 'E': 'Kusam'}, 
             'A', 'Indah dan cantik memiliki makna yang sama.'),
            ('Antonim dari kata "terang" adalah...', 
             {'A': 'Cerah', 'B': 'Gelap', 'C': 'Sinar', 'D': 'Cahaya', 'E': 'Lampu'}, 
             'B', 'Terang berlawanan dengan gelap.'),
            ('Sinonim dari kata "cepat" adalah...', 
             {'A': 'Lambat', 'B': 'Pelan', 'C': 'Gesit', 'D': 'Santai', 'E': 'Tenang'}, 
             'C', 'Cepat dan gesit memiliki makna yang mirip.'),
            ('Sinonim dari kata "pintar" adalah...', 
             {'A': 'Bodoh', 'B': 'Dungu', 'C': 'Cerdas', 'D': 'Tolol', 'E': 'Lamban'}, 
             'C', 'Pintar dan cerdas memiliki makna yang sama.'),
            ('Antonim dari kata "tinggi" adalah...', 
             {'A': 'Rendah', 'B': 'Besar', 'C': 'Lebar', 'D': 'Panjang', 'E': 'Jauh'}, 
             'A', 'Tinggi berlawanan dengan rendah.'),
            ('Sinonim dari kata "rajin" adalah...', 
             {'A': 'Malas', 'B': 'Giat', 'C': 'Santai', 'D': 'Leha-leha', 'E': 'Bosan'}, 
             'B', 'Rajin dan giat memiliki makna yang sama.'),
            ('Antonim dari kata "kaya" adalah...', 
             {'A': 'Mampu', 'B': 'Miskin', 'C': 'Berada', 'D': 'Cukup', 'E': 'Lebih'}, 
             'B', 'Kaya berlawanan dengan miskin.'),
            ('Sinonim dari kata "berani" adalah...', 
             {'A': 'Takut', 'B': 'Gentar', 'C': 'Pemberani', 'D': 'Penakut', 'E': 'Ciut'}, 
             'C', 'Berani dan pemberani memiliki makna yang sama.'),
            ('Sinonim dari kata "luas" adalah...', 
             {'A': 'Sempit', 'B': 'Kecil', 'C': 'Lebar', 'D': 'Pendek', 'E': 'Tipis'}, 
             'C', 'Luas dan lebar memiliki makna yang mirip.'),
            ('Antonim dari kata "panas" adalah...', 
             {'A': 'Hangat', 'B': 'Dingin', 'C': 'Suam', 'D': 'Api', 'E': 'Kompor'}, 
             'B', 'Panas berlawanan dengan dingin.'),
            ('Sinonim dari kata "cantik" adalah...', 
             {'A': 'Jelek', 'B': 'Buruk', 'C': 'Elok', 'D': 'Busuk', 'E': 'Rusak'}, 
             'C', 'Cantik dan elok memiliki makna yang sama.'),
            ('Antonim dari kata "maju" adalah...', 
             {'A': 'Depan', 'B': 'Mundur', 'C': 'Jauh', 'D': 'Dekat', 'E': 'Samping'}, 
             'B', 'Maju berlawanan dengan mundur.'),
            ('Sinonim dari kata "kuat" adalah...', 
             {'A': 'Lemah', 'B': 'Loyo', 'C': 'Perkasa', 'D': 'Lelah', 'E': 'Letih'}, 
             'C', 'Kuat dan perkasa memiliki makna yang sama.'),
            ('Sinonim dari kata "bersih" adalah...', 
             {'A': 'Kotor', 'B': 'Kusam', 'C': 'Higienis', 'D': 'Dekil', 'E': 'Noda'}, 
             'C', 'Bersih dan higienis memiliki makna yang sama.'),
            ('Antonim dari kata "baik" adalah...', 
             {'A': 'Bagus', 'B': 'Buruk', 'C': 'Indah', 'D': 'Cantik', 'E': 'Elok'}, 
             'B', 'Baik berlawanan dengan buruk.'),
            ('Sinonim dari kata "sulit" adalah...', 
             {'A': 'Mudah', 'B': 'Gampang', 'C': 'Rumit', 'D': 'Ringan', 'E': 'Simpel'}, 
             'C', 'Sulit dan rumit memiliki makna yang sama.'),
            ('Antonim dari kata "jauh" adalah...', 
             {'A': 'Dekat', 'B': 'Panjang', 'C': 'Lebar', 'D': 'Tinggi', 'E': 'Besar'}, 
             'A', 'Jauh berlawanan dengan dekat.'),
            ('Sinonim dari kata "keras" adalah...', 
             {'A': 'Lunak', 'B': 'Empuk', 'C': 'Padat', 'D': 'Lembut', 'E': 'Halus'}, 
             'C', 'Keras dan padat memiliki makna yang mirip.'),
        ]
    },
    # Wawasan Kebangsaan (20 questions)
    {
        'subject': 'wawasan_kebangsaan',
        'subtype': None,
        'questions': [
            ('Sila pertama Pancasila adalah...', 
             {'A': 'Ketuhanan Yang Maha Esa', 'B': 'Kemanusiaan', 'C': 'Persatuan', 'D': 'Kerakyatan', 'E': 'Keadilan'}, 
             'A', 'Sila pertama Pancasila adalah Ketuhanan Yang Maha Esa.'),
            ('Ibukota Indonesia adalah...', 
             {'A': 'Bandung', 'B': 'Surabaya', 'C': 'Jakarta', 'D': 'Medan', 'E': 'Semarang'}, 
             'C', 'Jakarta adalah ibukota negara Indonesia.'),
            ('Proklamator Indonesia adalah...', 
             {'A': 'Soekarno dan Hatta', 'B': 'Soeharto', 'C': 'Habibie', 'D': 'Megawati', 'E': 'SBY'}, 
             'A', 'Soekarno dan Mohammad Hatta adalah proklamator kemerdekaan Indonesia.'),
            ('Indonesia merdeka pada tanggal...', 
             {'A': '1 Juni 1945', 'B': '17 Agustus 1945', 'C': '17 Agustus 1946', 'D': '1 Oktober 1945', 'E': '20 Mei 1945'}, 
             'B', 'Indonesia merdeka pada 17 Agustus 1945.'),
            ('Lambang negara Indonesia adalah...', 
             {'A': 'Garuda', 'B': 'Elang', 'C': 'Rajawali', 'D': 'Burung Hantu', 'E': 'Merak'}, 
             'A', 'Garuda Pancasila adalah lambang negara Indonesia.'),
            ('Lagu kebangsaan Indonesia adalah...', 
             {'A': 'Indonesia Raya', 'B': 'Garuda Pancasila', 'C': 'Bagimu Negeri', 'D': 'Tanah Air', 'E': 'Maju Tak Gentar'}, 
             'A', 'Indonesia Raya adalah lagu kebangsaan Indonesia.'),
            ('Pancasila terdiri dari berapa sila?', 
             {'A': '3', 'B': '4', 'C': '5', 'D': '6', 'E': '7'}, 
             'C', 'Pancasila terdiri dari 5 sila.'),
            ('Bhinneka Tunggal Ika artinya...', 
             {'A': 'Berbeda-beda tetapi tetap satu', 'B': 'Sama rata sama rasa', 'C': 'Bersatu kita teguh', 'D': 'Gotong royong', 'E': 'Musyawarah mufakat'}, 
             'A', 'Bhinneka Tunggal Ika berarti berbeda-beda tetapi tetap satu.'),
            ('Hari Pahlawan diperingati setiap tanggal...', 
             {'A': '10 November', 'B': '17 Agustus', 'C': '1 Juni', 'D': '20 Mei', 'E': '28 Oktober'}, 
             'A', 'Hari Pahlawan diperingati setiap 10 November.'),
            ('Presiden pertama Indonesia adalah...', 
             {'A': 'Mohammad Hatta', 'B': 'Soekarno', 'C': 'Soeharto', 'D': 'Habibie', 'E': 'Gus Dur'}, 
             'B', 'Ir. Soekarno adalah presiden pertama Indonesia.'),
        ] + [
            (f'Pertanyaan TWK test {i}?', 
             {'A': 'Jawaban A', 'B': 'Jawaban B', 'C': 'Jawaban C', 'D': 'Jawaban D', 'E': 'Jawaban E'}, 
             'A', f'Penjelasan untuk pertanyaan {i}.')
            for i in range(11, 21)
        ]
    },
    # TKP (20 questions)
    {
        'subject': 'tkp',
        'subtype': None,
        'questions': [
            (f'Jika atasan Anda memberikan tugas mendadak di akhir jam kerja, Anda akan...', 
             {'A': 'Menolak dengan halus', 'B': 'Menerima dan mengerjakannya', 'C': 'Mengabaikan', 'D': 'Marah-marah', 'E': 'Mengajukan pengunduran diri'}, 
             'B', 'Sikap profesional adalah menerima tugas dari atasan.'),
        ] + [
            (f'Situasi TKP test {i}: Bagaimana sikap Anda?', 
             {'A': 'Sikap sangat baik', 'B': 'Sikap baik', 'C': 'Sikap cukup', 'D': 'Sikap kurang', 'E': 'Sikap buruk'}, 
             'A', f'Penjelasan untuk situasi {i}.')
            for i in range(2, 21)
        ]
    }
]

total_added = 0

for subject_group in test_questions:
    subject = subject_group['subject']
    subtype = subject_group['subtype']
    
    print(f"📚 Adding {subject.upper()} questions...")
    
    for i, (q_text, options, correct, explanation) in enumerate(subject_group['questions']):
        difficulty = ['mudah', 'sedang', 'sulit'][i % 3]
        
        question = Question(
            question_id=f"q_test_{secrets.token_hex(6)}",
            test_category='cpns',
            subject=subject,
            subtype=subtype,
            difficulty=difficulty,
            question_text=q_text,
            options=options,
            correct_answer=correct,
            explanation=explanation,
            content_hash=create_hash(q_text, correct),
            quality_score=0.85,
            is_used=False,
            usage_count=0
        )
        
        try:
            db.add(question)
            total_added += 1
        except Exception as e:
            print(f"   ⚠️  Skipped duplicate: {q_text[:30]}...")
    
    db.commit()
    print(f"   ✅ Added {len(subject_group['questions'])} {subject} questions\n")

db.close()

print("=" * 60)
print(f"✅ Successfully added {total_added} test questions!")
print("=" * 60)
print("\nBreakdown:")
print("  • TIU Verbal: 20 questions")
print("  • Wawasan Kebangsaan: 20 questions")
print("  • TKP: 20 questions")
print("\nYou can now:")
print("  • Create sessions with 50+ questions")
print("  • Test session system fully")
print("  • Run: python core/session_manager.py")
print("=" * 60 + "\n")