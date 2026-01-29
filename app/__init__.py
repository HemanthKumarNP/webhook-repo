from flask import Flask
from app.extensions import mongo
from app.webhook.routes import webhook
from dotenv import load_dotenv
import os

def create_app():
    load_dotenv() 

    app = Flask(__name__, template_folder="templates")

    app.config["MONGO_URI"] = os.getenv("MONGO_URI")

    if not app.config["MONGO_URI"]:
        raise RuntimeError("MONGO_URI not set in environment")

    mongo.init_app(app)
    app.register_blueprint(webhook)

    return app
