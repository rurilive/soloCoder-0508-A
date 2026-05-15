from datetime import datetime, timedelta

from flask import Blueprint, render_template


gantt_bp = Blueprint('gantt', __name__)


@gantt_bp.route('/gantt')
def gantt():
    now = datetime.now()
    start_date = (now - timedelta(days=30)).strftime('%Y-%m-%d')
    end_date = (now + timedelta(days=60)).strftime('%Y-%m-%d')
    
    return render_template('gantt.html', 
                         start_date=start_date, 
                         end_date=end_date,
                         today=now.strftime('%Y-%m-%d'))
