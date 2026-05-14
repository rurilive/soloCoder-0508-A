from datetime import datetime, timedelta
from typing import Optional

from flask import Blueprint, render_template

from app.models import get_all_events
from app.utils import get_events_by_date_range


calendar_bp = Blueprint('calendar', __name__)


@calendar_bp.route('/')
@calendar_bp.route('/calendar/<int:year>/<int:month>')
def calendar(year: Optional[int] = None, month: Optional[int] = None):
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
    
    all_events = get_all_events()
    
    month_start = f'{year}-{month:02d}-01'
    month_end = f'{year}-{month:02d}-{last_day.day:02d}'
    events_by_date = get_events_by_date_range(all_events, month_start, month_end)
    
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
