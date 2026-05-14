import sqlite3
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

from flask import current_app


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(current_app.config['DATABASE_PATH'])
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            date TEXT NOT NULL,
            time TEXT,
            description TEXT,
            duration INTEGER DEFAULT 0,
            end_date TEXT,
            reminder_type TEXT DEFAULT 'none',
            reminder_value INTEGER DEFAULT 0,
            repeat_type TEXT DEFAULT 'none',
            repeat_end_date TEXT,
            is_completed INTEGER DEFAULT 0,
            completion_note TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS event_completions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER NOT NULL,
            completion_date TEXT NOT NULL,
            completion_note TEXT,
            completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (event_id) REFERENCES events (id) ON DELETE CASCADE,
            UNIQUE(event_id, completion_date)
        )
    ''')
    
    conn.commit()
    conn.close()
