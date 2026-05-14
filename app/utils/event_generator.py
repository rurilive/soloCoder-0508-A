from datetime import datetime, timedelta
from typing import Any, Dict, List

from app.models.event import get_event_completion


def generate_cross_day_events(event: Dict[str, Any], start_date: str, end_date: str) -> List[Dict[str, Any]]:
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
        
        completion = get_event_completion(event['id'], date_str)
        if completion:
            new_event['is_completed'] = 1
            new_event['completion_note'] = completion['completion_note']
        else:
            new_event['is_completed'] = 0
            new_event['completion_note'] = None
        
        events.append(new_event)
        current_date += timedelta(days=1)
    
    return events


def generate_repeated_events(event: Dict[str, Any], start_date: str, end_date: str) -> List[Dict[str, Any]]:
    if event['repeat_type'] == 'none':
        return generate_cross_day_events(event, start_date, end_date)
    
    events = []
    current_date = datetime.strptime(event['date'], '%Y-%m-%d').date()
    end_limit = datetime.strptime(end_date, '%Y-%m-%d').date()
    
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
