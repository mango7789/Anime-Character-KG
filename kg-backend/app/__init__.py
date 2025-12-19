from flask import Flask
from flask_cors import CORS
from .routes import bp


def create_app():
    app = Flask(__name__)
    app.config["JSON_AS_ASCII"] = False
    # Allow communication cross domains
    CORS(app)

    app.register_blueprint(bp)

    return app
