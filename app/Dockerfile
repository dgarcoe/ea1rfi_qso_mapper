FROM python:3.11-slim-bookworm

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    sqlite3 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY . .
RUN pip install --no-cache-dir -r requirements.txt

RUN mkdir -p /data

RUN sqlite3 /data/usage.db "\
CREATE TABLE IF NOT EXISTS uploads ( \
    id INTEGER PRIMARY KEY AUTOINCREMENT, \
    timestamp TEXT, \
    callsign TEXT, \
    filename TEXT, \
    qso_count INTEGER, \
    ip TEXT, \
    user_agent TEXT \
);"

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
