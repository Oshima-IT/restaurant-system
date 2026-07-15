from app import app
from models.database import db

# モデルを読み込む
from models.user import User
from models.product import Product
from models.purchase import Purchase
from models.attendance import Attendance

with app.app_context():

    db.create_all()

    from app import ensure_purchase_columns
    ensure_purchase_columns()

    print("テーブル作成完了")