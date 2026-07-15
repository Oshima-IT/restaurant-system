from flask import Flask

from config import Config
from models.database import db

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

with app.app_context():
    try:
        db.session.execute(db.text("SELECT 1"))
        print("MySQL接続成功！")
    except Exception as e:
        print(e)