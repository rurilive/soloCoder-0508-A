from datetime import datetime, timedelta

from flask import Blueprint, render_template, request, redirect, url_for

from app.models import (
    get_all_events,
    get_event_by_id,
    get_all_completions_for_event,
    create_event,
    update_event,
    delete_event,
    complete_event,
    uncomplete_event
)
from app.utils import get_events_for_date


events_bp = Blueprint('events', __name__)


@events_bp.route('/day/<date>')
def day_events(date: str):
    all_events = get_all_events()
    events = get_events_for_date(all_events, date)
    current_time = datetime.now().strftime('%H:%M')
    return render_template('day.html', date=date, events=events, current_time=current_time)


@events_bp.route('/add', methods=['GET', 'POST'])
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
        
        create_event(
            title=title,
            date=date,
            time=time,
            description=description,
            duration=duration,
            end_date=end_date,
            reminder_type=reminder_type,
            reminder_value=reminder_value,
            repeat_type=repeat_type,
            repeat_end_date=repeat_end_date
        )
        
        return redirect(url_for('events.day_events', date=date))
    
    date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    time = request.args.get('time', datetime.now().strftime('%H:%M'))
    return render_template('add_event.html', date=date, time=time)


@events_bp.route('/edit/<int:event_id>', methods=['GET', 'POST'])
def edit_event(event_id: int):
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
        
        update_event(
            event_id=event_id,
            title=title,
            date=date,
            time=time,
            description=description,
            duration=duration,
            end_date=end_date,
            reminder_type=reminder_type,
            reminder_value=reminder_value,
            repeat_type=repeat_type,
            repeat_end_date=repeat_end_date
        )
        
        return redirect(url_for('events.day_events', date=date))
    
    event = get_event_by_id(event_id)
    return render_template('edit_event.html', event=event)


@events_bp.route('/complete/<int:event_id>/<date>', methods=['POST'])
def complete(event_id: int, date: str):
    completion_note = request.form.get('completion_note', '')
    complete_event(event_id, date, completion_note)
    return redirect(url_for('events.day_events', date=date))


@events_bp.route('/uncomplete/<int:event_id>/<date>')
def uncomplete(event_id: int, date: str):
    uncomplete_event(event_id, date)
    return redirect(url_for('events.day_events', date=date))


@events_bp.route('/event/<int:event_id>')
def event_detail(event_id: int):
    event = get_event_by_id(event_id)
    
    if not event:
        return redirect(url_for('calendar.calendar'))
    
    completions = get_all_completions_for_event(event_id)
    
    now = datetime.now().date()
    event_start = datetime.strptime(event['date'], '%Y-%m-%d').date()
    repeat_end = None
    if event['repeat_end_date']:
        repeat_end = datetime.strptime(event['repeat_end_date'], '%Y-%m-%d').date()
    
    total_days = 0
    completed_days = len(completions)
    
    if event['repeat_type'] != 'none':
        end_limit = repeat_end or (now + timedelta(days=365))
        current = event_start
        while current <= end_limit:
            total_days += 1
            if event['repeat_type'] == 'daily':
                current += timedelta(days=1)
            elif event['repeat_type'] == 'weekly':
                current += timedelta(weeks=1)
            elif event['repeat_type'] == 'monthly':
                try:
                    if current.month == 12:
                        current = current.replace(year=current.year + 1, month=1)
                    else:
                        current = current.replace(month=current.month + 1)
                except ValueError:
                    while True:
                        current += timedelta(days=1)
                        if current.day == 1:
                            break
    elif event['end_date']:
        event_end = datetime.strptime(event['end_date'], '%Y-%m-%d').date()
        total_days = (event_end - event_start).days + 1
    else:
        total_days = 1
    
    return render_template('event_detail.html', 
                         event=event, 
                         completions=completions,
                         total_days=total_days,
                         completed_days=completed_days)


@events_bp.route('/delete/<int:event_id>')
def delete(event_id: int):
    date = delete_event(event_id)
    if not date:
        date = datetime.now().strftime('%Y-%m-%d')
    return redirect(url_for('events.day_events', date=date))
