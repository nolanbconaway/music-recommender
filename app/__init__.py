from flask import Flask, render_template
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
limiter = Limiter(key_func=get_remote_address, default_limits=["1000 per day"])


@limiter.request_filter
def ip_whitelist():
    """Add some exemptions to the limiter."""
    from flask import request

    return request.remote_addr in ("127.0.0.1", "localhost")


def create_app():
    """App factory boiiiii."""
    app = Flask(__name__)
    app.config.from_pyfile("config.py")

    from . import routes

    db.init_app(app)
    limiter.init_app(app)
    app.register_blueprint(routes.bp)

    return app
