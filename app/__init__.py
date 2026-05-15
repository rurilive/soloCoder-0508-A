import os
from flask import Flask
from typing import Optional

from app.config.settings import get_config
from app.models.database import init_db
from app.routes.calendar import calendar_bp
from app.routes.events import events_bp
from app.routes.api import api_bp
from app.routes.gantt import gantt_bp

def create_app(config: Optional[object] = None) -> Flask:
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    app = Flask(
        __name__,
        template_folder=os.path.join(base_dir, 'templates'),
        static_folder=os.path.join(base_dir, 'static')
    )
    
    if config is None:
        config = get_config()
    app.config.from_object(config)
    
    with app.app_context():
        init_db()
    
    app.register_blueprint(calendar_bp)
    app.register_blueprint(events_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(gantt_bp)
    
    return app
