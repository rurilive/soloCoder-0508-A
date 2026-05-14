from datetime import datetime, timedelta
from typing import Any, Dict, List

from app.models.event import get_event_completion


def _create_event_instance(
    event: Dict[str, Any],
    event_date: str,
    is_original: bool,
    is_cross_day: bool
) -> Dict[str, Any]:
    new_event = dict(event)
    new_event['date'] = event_date
    new_event['is_original'] = is_original
    new_event['is_cross_day'] = is_cross_day
    
    completion = get_event_completion(event['id'], event_date)
    if completion:
        new_event['is_completed'] = 1
        new_event['completion_note'] = completion['completion_note']
    else:
        new_event['is_completed'] = 0
        new_event['completion_note'] = None
    
    return new_event


def generate_cross_day_events(event: Dict[str, Any], start_date: str, end_date: str) -> List[Dict[str, Any]]:
    events = []
    event_start = datetime.strptime(event['date'], '%Y-%m-%d').date()
    event_end = event_start
    if event['end_date']:
        event_end = datetime.strptime(event['end_date'], '%Y-%m-%d').date()
    
    start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
    end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    is_cross_day = event_start != event_end
    current_date = max(event_start, start_dt)
    while current_date <= min(event_end, end_dt):
        date_str = current_date.strftime('%Y-%m-%d')
        is_original = (date_str == event['date'])
        events.append(_create_event_instance(event, date_str, is_original, is_cross_day))
        current_date += timedelta(days=1)
    
    return events


def generate_repeated_events(event: Dict[str, Any], start_date: str, end_date: str) -> List[Dict[str, Any]]:
    if event['repeat_type'] == 'none':
        return generate_cross_day_events(event, start_date, end_date)
    
    original_start = datetime.strptime(event['date'], '%Y-%m-%d').date()
    
    events = []
    current_repeat_date = original_start
    end_limit = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    if event['repeat_end_date']:
        repeat_end = datetime.strptime(event['repeat_end_date'], '%Y-%m-%d').date()
        end_limit = min(end_limit, repeat_end)
    
    start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
    
    while current_repeat_date <= end_limit:
        if current_repeat_date >= start_dt:
            date_str = current_repeat_date.strftime('%Y-%m-%d')
            is_original = (current_repeat_date == original_start)
            events.append(_create_event_instance(event, date_str, is_original, is_cross_day=False))
        
        if event['repeat_type'] == 'daily':
            current_repeat_date += timedelta(days=1)
        elif event['repeat_type'] == 'weekly':
            current_repeat_date += timedelta(weeks=1)
        elif event['repeat_type'] == 'monthly':
            try:
                if current_repeat_date.month == 12:
                    current_repeat_date = current_repeat_date.replace(year=current_repeat_date.year + 1, month=1)
                else:
                    current_repeat_date = current_repeat_date.replace(month=current_repeat_date.month + 1)
            except ValueError:
                while True:
                    current_repeat_date += timedelta(days=1)
                    if current_repeat_date.day == 1:
                        break
    
    return events


def get_events_for_date(all_events: List[Dict[str, Any]], target_date: str) -> List[Dict[str, Any]]:
    events = []
    for event in all_events:
        repeated_events = generate_repeated_events(event, target_date, target_date)
        events.extend(repeated_events)
    
    events.sort(key=lambda x: x['time'] or '00:00')
    return events


def get_events_by_date_range(all_events: List[Dict[str, Any]], start_date: str, end_date: str) -> Dict[str, Any]:
    events_by_date = {}
    for event in all_events:
        repeated_events = generate_repeated_events(event, start_date, end_date)
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
                'repeat_type': rep_event['repeat_type'],
                'id': rep_event['id']
            })
    
    return events_by_date
