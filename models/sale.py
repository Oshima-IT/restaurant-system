from models.database import db
from datetime import datetime


class Sale(db.Model):

    __tablename__ = "sales"

    id = db.Column(db.Integer, primary_key=True)

    total_price = db.Column(
        db.Integer,
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.now
    )