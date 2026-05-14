from datetime import datetime, timedelta
from typing import Any, Dict, List


def get_active_reminders(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    now = datetime.now()
    reminders = []
    
    for event in events:
        if event['reminder_type'] == 'none' or event.get('is_completed', 0) == 1:
            continue
        
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
    
    return reminders
