from flask import Blueprint, jsonify

from app.models import get_all_events
from app.utils import get_active_reminders


api_bp = Blueprint('api', __name__)


@api_bp.route('/api/reminders')
def get_reminders():
    events = get_all_events()
    reminders = get_active_reminders(events)
    return jsonify(reminders)
