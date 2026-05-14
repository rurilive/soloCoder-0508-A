import sqlite3
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

from app.models.database import get_db


def get_event_completion(event_id: int, date: str) -> Optional[Dict[str, Any]]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM event_completions 
        WHERE event_id = ? AND completion_date = ?
    ''', (event_id, date))
    completion = cursor.fetchone()
    conn.close()
    return dict(completion) if completion else None


def get_all_completions_for_event(event_id: int) -> List[Dict[str, Any]]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM event_completions 
        WHERE event_id = ? 
        ORDER BY completion_date DESC
    ''', (event_id,))
    completions = cursor.fetchall()
    conn.close()
    return [dict(c) for c in completions]


def get_all_events() -> List[Dict[str, Any]]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM events ORDER BY date, time')
    events = cursor.fetchall()
    conn.close()
    return [dict(e) for e in events]


def get_event_by_id(event_id: int) -> Optional[Dict[str, Any]]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM events WHERE id = ?', (event_id,))
    event = cursor.fetchone()
    conn.close()
    return dict(event) if event else None


def create_event(
    title: str,
    date: str,
    time: str = '',
    description: str = '',
    duration: int = 0,
    end_date: Optional[str] = None,
    reminder_type: str = 'none',
    reminder_value: int = 0,
    repeat_type: str = 'none',
    repeat_end_date: Optional[str] = None
) -> int:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO events (title, date, time, description, duration, end_date,
                           reminder_type, reminder_value, repeat_type, repeat_end_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (title, date, time, description, duration, end_date,
          reminder_type, reminder_value, repeat_type, repeat_end_date))
    event_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return event_id


def update_event(
    event_id: int,
    title: str,
    date: str,
    time: str = '',
    description: str = '',
    duration: int = 0,
    end_date: Optional[str] = None,
    reminder_type: str = 'none',
    reminder_value: int = 0,
    repeat_type: str = 'none',
    repeat_end_date: Optional[str] = None
) -> bool:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE events 
        SET title = ?, date = ?, time = ?, description = ?, 
            duration = ?, end_date = ?, reminder_type = ?, 
            reminder_value = ?, repeat_type = ?, repeat_end_date = ?
        WHERE id = ?
    ''', (title, date, time, description, duration, end_date,
          reminder_type, reminder_value, repeat_type, repeat_end_date, event_id))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0


def delete_event(event_id: int) -> Optional[str]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT date FROM events WHERE id = ?', (event_id,))
    event = cursor.fetchone()
    date = None
    if event:
        cursor.execute('DELETE FROM events WHERE id = ?', (event_id,))
        conn.commit()
        date = event['date']
    conn.close()
    return date


def complete_event(event_id: int, date: str, completion_note: str = '') -> bool:
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT id FROM events WHERE id = ?', (event_id,))
    event = cursor.fetchone()
    
    if event:
        cursor.execute('''
            INSERT OR REPLACE INTO event_completions (event_id, completion_date, completion_note)
            VALUES (?, ?, ?)
        ''', (event_id, date, completion_note))
        conn.commit()
    
    conn.close()
    return event is not None


def uncomplete_event(event_id: int, date: str) -> None:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM event_completions WHERE event_id = ? AND completion_date = ?', 
                   (event_id, date))
    conn.commit()
    conn.close()
