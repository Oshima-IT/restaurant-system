from flask import Flask
from werkzeug.security import generate_password_hash

from config import Config
from models.database import db
from models.user import User

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

with app.app_context():

    admin = User.query.filter_by(username="admin").first()
    if admin:
        print("管理者アカウントは既に存在します。")
    else:
        admin = User(
            username="admin",
            password=generate_password_hash("admin123"),
            name="管理者",
            role="admin"
        )
        db.session.add(admin)

    manager = User.query.filter_by(username="manager").first()
    if not manager:
        manager = User(
            username="manager",
            password=generate_password_hash("manager123"),
            name="店長",
            role="manager"
        )
        db.session.add(manager)

    staff_a = User.query.filter_by(username="staff_a").first()
    if not staff_a:
        staff_a = User(
            username="staff_a",
            password=generate_password_hash("staffa123"),
            name="アルバイトA",
            role="staff"
        )
        db.session.add(staff_a)

    staff_b = User.query.filter_by(username="staff_b").first()
    if not staff_b:
        staff_b = User(
            username="staff_b",
            password=generate_password_hash("staffb123"),
            name="アルバイトB",
            role="staff"
        )
        db.session.add(staff_b)

    db.session.commit()

    print("管理者アカウントを作成しました。")
    print("店長アカウントを作成しました。")
    print("アルバイトAアカウントを作成しました。")
    print("アルバイトBアカウントを作成しました。")