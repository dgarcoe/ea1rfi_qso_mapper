import sqlite3
from datetime import datetime

DB_PATH = "/data/usage.db"

def log_upload(callsign, filename, qso_count, request_headers=None):

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS uploads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            callsign TEXT,
            filename TEXT,
            qso_count INTEGER,
            ip TEXT,
            user_agent TEXT
        )
    """)

    ip = None
    ua = None
    if request_headers:
        ip = request_headers.get("X-Forwarded-For", "")
        ua = request_headers.get("User-Agent", "")

    cur.execute("""
        INSERT INTO uploads (timestamp, callsign, filename, qso_count, ip, user_agent)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        datetime.utcnow().isoformat(),
        callsign,
        filename,
        qso_count,
        ip,
        ua
    ))

    conn.commit()
    conn.close()