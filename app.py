import sqlite3
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for

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
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()


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
    cursor.execute('''
        SELECT date, COUNT(*) as count, GROUP_CONCAT(title, '|||') as titles 
        FROM events 
        WHERE date LIKE ? 
        GROUP BY date
    ''', (f'{year}-{month:02d}-%',))
    events_data = cursor.fetchall()
    conn.close()
    
    events_by_date = {}
    for row in events_data:
        events_by_date[row['date']] = {
            'count': row['count'],
            'titles': row['titles'].split('|||')
        }
    
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
    cursor.execute('SELECT * FROM events WHERE date = ? ORDER BY time', (date,))
    events = cursor.fetchall()
    conn.close()
    
    return render_template('day.html', date=date, events=events)


@app.route('/add', methods=['GET', 'POST'])
def add_event():
    if request.method == 'POST':
        title = request.form['title']
        date = request.form['date']
        time = request.form.get('time', '')
        description = request.form.get('description', '')
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO events (title, date, time, description)
            VALUES (?, ?, ?, ?)
        ''', (title, date, time, description))
        conn.commit()
        conn.close()
        
        return redirect(url_for('day_events', date=date))
    
    date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    return render_template('add_event.html', date=date)


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
