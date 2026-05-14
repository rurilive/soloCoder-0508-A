from app import create_app
from app.config.settings import get_config


if __name__ == '__main__':
    config = get_config()
    app = create_app(config)
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)
