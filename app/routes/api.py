from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request

from app.models import get_all_events, get_event_by_id
from app.models.blockchain import (
    add_event_note_to_blockchain,
    get_event_notes_from_blockchain,
    get_blockchain_status
)
from app.utils import get_active_reminders


api_bp = Blueprint('api', __name__)


@api_bp.route('/api/reminders')
def get_reminders():
    events = get_all_events()
    reminders = get_active_reminders(events)
    return jsonify(reminders)


@api_bp.route('/api/gantt/events')
def get_gantt_events():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if not start_date or not end_date:
        now = datetime.now()
        start_date = (now - timedelta(days=30)).strftime('%Y-%m-%d')
        end_date = (now + timedelta(days=60)).strftime('%Y-%m-%d')
    
    all_events = get_all_events()
    gantt_events = []
    
    for event in all_events:
        event_start = event['date']
        event_end = event.get('end_date') or event['date']
        
        if event_start <= end_date and event_end >= start_date:
            gantt_events.append({
                'id': event['id'],
                'title': event['title'],
                'start': event_start,
                'end': event_end,
                'time': event.get('time', ''),
                'duration': event.get('duration', 0),
                'description': event.get('description', ''),
                'is_completed': event.get('is_completed', 0),
                'repeat_type': event.get('repeat_type', 'none')
            })
    
    return jsonify({
        'events': gantt_events,
        'start_date': start_date,
        'end_date': end_date
    })


@api_bp.route('/api/events/<int:event_id>/notes', methods=['GET'])
def get_event_notes(event_id: int):
    event = get_event_by_id(event_id)
    if not event:
        return jsonify({'error': 'Event not found'}), 404
    
    notes = get_event_notes_from_blockchain(event_id)
    return jsonify({
        'event_id': event_id,
        'notes': notes
    })


@api_bp.route('/api/events/<int:event_id>/notes', methods=['POST'])
def add_event_note(event_id: int):
    event = get_event_by_id(event_id)
    if not event:
        return jsonify({'error': 'Event not found'}), 404
    
    data = request.get_json()
    if not data or 'note' not in data:
        return jsonify({'error': 'Note content is required'}), 400
    
    note = data['note'].strip()
    if not note:
        return jsonify({'error': 'Note cannot be empty'}), 400
    
    created_by = data.get('created_by', 'user')
    result = add_event_note_to_blockchain(event_id, note, created_by)
    
    return jsonify({
        'success': True,
        'block': result
    }), 201


@api_bp.route('/api/blockchain/status')
def blockchain_status():
    status = get_blockchain_status()
    return jsonify(status)
