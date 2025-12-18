from flask import Flask
from flask_cors import CORS
from .routes import bp


def create_app():
    app = Flask(__name__)
    # Allow communication cross domains
    CORS(app)

    app.register_blueprint(bp)

    return app
