from flask import Flask
from db import db
import os
from views.byr.routes import byr
from flask_cors import CORS
from auth_obj import SECRET_KEY
from views.api.routes import api

def create_app():
    app = Flask(__name__)
    CORS(app)
    app.config["SECRET_KEY"] = SECRET_KEY
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///byr.db"
    app.register_blueprint(byr)
    app.register_blueprint(api, url_prefix="/api")
    db.init_app(app)
    return app

def set_db(app):
    with app.app_context():
        db.create_all()

# if __name__ == "__main__":
#     app = create_app()
#     if not os.path.isfile("byr.db"):
#         set_db(app)
#     app.run(debug=True) #default port=5000