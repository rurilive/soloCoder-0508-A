import sqlite3
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, jsonify

app = Flask(__name__)


def get_db():
    conn = sqlite3.connect('calendar.db')
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
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
    conn.commit()
    conn.close()


def generate_cross_day_events(event, start_date, end_date):
    events = []
    event_start = datetime.strptime(event['date'], '%Y-%m-%d').date()
    event_end = event_start
    if event['end_date']:
        event_end = datetime.strptime(event['end_date'], '%Y-%m-%d').date()
    
    start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
    end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    current_date = max(event_start, start_dt)
    while current_date <= min(event_end, end_dt):
        date_str = current_date.strftime('%Y-%m-%d')
        new_event = dict(event)
        new_event['date'] = date_str
        new_event['is_original'] = (date_str == event['date'])
        new_event['is_cross_day'] = event_start != event_end
        events.append(new_event)
        current_date += timedelta(days=1)
    
    return events

def generate_repeated_events(event, start_date, end_date):
    events = []
    
    if event['repeat_type'] == 'none':
        return generate_cross_day_events(event, start_date, end_date)
    
    current_date = datetime.strptime(event['date'], '%Y-%m-%d').date()
    end_limit = datetime.strptime(end_date, '%Y-%m-%d').date()
    repeat_end = None
    if event['repeat_end_date']:
        repeat_end = datetime.strptime(event['repeat_end_date'], '%Y-%m-%d').date()
        end_limit = min(end_limit, repeat_end)
    
    start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
    
    while current_date <= end_limit:
        if current_date >= start_dt:
            temp_event = dict(event)
            temp_event['date'] = current_date.strftime('%Y-%m-%d')
            temp_event['is_original'] = (current_date == datetime.strptime(event['date'], '%Y-%m-%d').date())
            cross_day_events = generate_cross_day_events(temp_event, start_date, end_date)
            events.extend(cross_day_events)
        
        if event['repeat_type'] == 'daily':
            current_date += timedelta(days=1)
        elif event['repeat_type'] == 'weekly':
            current_date += timedelta(weeks=1)
        elif event['repeat_type'] == 'monthly':
            try:
                if current_date.month == 12:
                    current_date = current_date.replace(year=current_date.year + 1, month=1)
                else:
                    current_date = current_date.replace(month=current_date.month + 1)
            except ValueError:
                while True:
                    current_date += timedelta(days=1)
                    if current_date.day == 1:
                        break
    
    return events


@app.route('/')
@app.route('/calendar/<int:year>/<int:month>')
def calendar(year=None, month=None):
    if year is None or month is None:
        now = datetime.now()
        year = now.year
        month = now.month
    
    first_day = datetime(year, month, 1)
    last_day = (first_day + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    
    start_weekday = first_day.weekday()
    
    prev_month = month - 1
    prev_year = year
    if prev_month == 0:
        prev_month = 12
        prev_year = year - 1
    
    next_month = month + 1
    next_year = year
    if next_month == 13:
        next_month = 1
        next_year = year + 1
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM events ORDER BY date, time')
    all_db_events = cursor.fetchall()
    conn.close()
    
    month_start = f'{year}-{month:02d}-01'
    month_end = f'{year}-{month:02d}-{last_day.day:02d}'
    
    events_by_date = {}
    for db_event in all_db_events:
        event = dict(db_event)
        repeated_events = generate_repeated_events(event, month_start, month_end)
        for rep_event in repeated_events:
            date = rep_event['date']
            if date not in events_by_date:
                events_by_date[date] = {
                    'count': 0,
                    'titles': [],
                    'full_events': []
                }
            events_by_date[date]['count'] += 1
            events_by_date[date]['titles'].append(rep_event['title'])
            events_by_date[date]['full_events'].append({
                'time': rep_event['time'],
                'title': rep_event['title'],
                'is_completed': rep_event['is_completed'],
                'repeat_type': rep_event['repeat_type']
            })
    
    days = []
    for i in range(start_weekday):
        days.append(None)
    
    for day in range(1, last_day.day + 1):
        date_str = f'{year}-{month:02d}-{day:02d}'
        days.append({
            'day': day,
            'date': date_str,
            'events': events_by_date.get(date_str, {'count': 0, 'titles': []})
        })
    
    return render_template('calendar.html',
                         year=year,
                         month=month,
                         month_name=first_day.strftime('%Y年%m月'),
                         prev_month=prev_month,
                         prev_year=prev_year,
                         next_month=next_month,
                         next_year=next_year,
                         days=days)


@app.route('/day/<date>')
def day_events(date):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM events ORDER BY date, time')
    all_db_events = cursor.fetchall()
    conn.close()
    
    events = []
    for db_event in all_db_events:
        event = dict(db_event)
        repeated_events = generate_repeated_events(event, date, date)
        for rep_event in repeated_events:
            events.append(rep_event)
    
    events.sort(key=lambda x: x['time'] or '00:00')
    current_time = datetime.now().strftime('%H:%M')
    return render_template('day.html', date=date, events=events, current_time=current_time)


@app.route('/add', methods=['GET', 'POST'])
def add_event():
    if request.method == 'POST':
        title = request.form['title']
        date = request.form['date']
        time = request.form.get('time', '')
        description = request.form.get('description', '')
        duration = int(request.form.get('duration', 0))
        end_date = request.form.get('end_date', '') or None
        reminder_type = request.form.get('reminder_type', 'none')
        reminder_value = int(request.form.get('reminder_value', 0))
        repeat_type = request.form.get('repeat_type', 'none')
        repeat_end_date = request.form.get('repeat_end_date', '') or None
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO events (title, date, time, description, duration, end_date,
                               reminder_type, reminder_value, repeat_type, repeat_end_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (title, date, time, description, duration, end_date,
              reminder_type, reminder_value, repeat_type, repeat_end_date))
        conn.commit()
        conn.close()
        
        return redirect(url_for('day_events', date=date))
    
    date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    time = request.args.get('time', datetime.now().strftime('%H:%M'))
    return render_template('add_event.html', date=date, time=time)


@app.route('/edit/<int:event_id>', methods=['GET', 'POST'])
def edit_event(event_id):
    conn = get_db()
    cursor = conn.cursor()
    
    if request.method == 'POST':
        title = request.form['title']
        date = request.form['date']
        time = request.form.get('time', '')
        description = request.form.get('description', '')
        duration = int(request.form.get('duration', 0))
        end_date = request.form.get('end_date', '') or None
        reminder_type = request.form.get('reminder_type', 'none')
        reminder_value = int(request.form.get('reminder_value', 0))
        repeat_type = request.form.get('repeat_type', 'none')
        repeat_end_date = request.form.get('repeat_end_date', '') or None
        
        cursor.execute('''
            UPDATE events 
            SET title = ?, date = ?, time = ?, description = ?, 
                duration = ?, end_date = ?, reminder_type = ?, 
                reminder_value = ?, repeat_type = ?, repeat_end_date = ?
            WHERE id = ?
        ''', (title, date, time, description, duration, end_date,
              reminder_type, reminder_value, repeat_type, repeat_end_date, event_id))
        conn.commit()
        conn.close()
        
        return redirect(url_for('day_events', date=date))
    
    cursor.execute('SELECT * FROM events WHERE id = ?', (event_id,))
    event = cursor.fetchone()
    conn.close()
    
    return render_template('edit_event.html', event=event)


@app.route('/complete/<int:event_id>', methods=['POST'])
def complete_event(event_id):
    completion_note = request.form.get('completion_note', '')
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT date FROM events WHERE id = ?', (event_id,))
    event = cursor.fetchone()
    
    if event:
        cursor.execute('''
            UPDATE events 
            SET is_completed = 1, completion_note = ? 
            WHERE id = ?
        ''', (completion_note, event_id))
        conn.commit()
        date = event['date']
    else:
        date = datetime.now().strftime('%Y-%m-%d')
    
    conn.close()
    return redirect(url_for('day_events', date=date))


@app.route('/uncomplete/<int:event_id>')
def uncomplete_event(event_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT date FROM events WHERE id = ?', (event_id,))
    event = cursor.fetchone()
    
    if event:
        cursor.execute('''
            UPDATE events 
            SET is_completed = 0, completion_note = NULL 
            WHERE id = ?
        ''', (event_id,))
        conn.commit()
        date = event['date']
    else:
        date = datetime.now().strftime('%Y-%m-%d')
    
    conn.close()
    return redirect(url_for('day_events', date=date))


@app.route('/api/reminders')
def get_reminders():
    now = datetime.now()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM events WHERE reminder_type != "none" AND is_completed = 0')
    events = cursor.fetchall()
    conn.close()
    
    reminders = []
    for event in events:
        if not event['time']:
            continue
        
        event_datetime = datetime.strptime(f"{event['date']} {event['time']}", '%Y-%m-%d %H:%M')
        reminder_time = None
        
        if event['reminder_type'] == 'minutes':
            reminder_time = event_datetime - timedelta(minutes=event['reminder_value'])
        elif event['reminder_type'] == 'hours':
            reminder_time = event_datetime - timedelta(hours=event['reminder_value'])
        elif event['reminder_type'] == 'days':
            reminder_time = event_datetime - timedelta(days=event['reminder_value'])
        
        if reminder_time and now >= reminder_time and now <= event_datetime:
            reminders.append({
                'id': event['id'],
                'title': event['title'],
                'event_time': event['time'],
                'event_date': event['date']
            })
    
    return jsonify(reminders)


@app.route('/delete/<int:event_id>')
def delete_event(event_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT date FROM events WHERE id = ?', (event_id,))
    event = cursor.fetchone()
    if event:
        cursor.execute('DELETE FROM events WHERE id = ?', (event_id,))
        conn.commit()
        date = event['date']
    else:
        date = datetime.now().strftime('%Y-%m-%d')
    conn.close()
    
    return redirect(url_for('day_events', date=date))


if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=1111, debug=True)
