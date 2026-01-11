FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# --- BAGIAN PENTING: JEBAKAN BATMAN ---
# Kita buat file script 'start.sh' langsung di dalam Linux
# Script ini fungsinya: Masa bodoh dengan argumen Railway, jalankan python main.py!
RUN echo '#!/bin/bash' > start.sh && \
    echo 'python main.py' >> start.sh && \
    chmod +x start.sh
# --------------------------------------

ENV PORT=8000
ENV HOST=0.0.0.0
EXPOSE 8000

# Jalankan script jebakan tadi
ENTRYPOINT ["./start.sh"]