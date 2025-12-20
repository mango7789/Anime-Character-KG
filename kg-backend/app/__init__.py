from flask import Flask
from flask_cors import CORS
from .routes import bp


def create_app():
    app = Flask(__name__)
    app.config["JSON_AS_ASCII"] = False

    app.register_blueprint(bp)
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    return app
