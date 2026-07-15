from datetime import datetime
from models.database import db


class Purchase(db.Model):

    __tablename__ = "purchases"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    product_name = db.Column(
        db.String(100),
        nullable=False
    )

    quantity = db.Column(
        db.Integer,
        nullable=False
    )

    supplier_name = db.Column(
        db.String(100),
        nullable=False,
        default=""
    )

    unit_price = db.Column(
        db.Float,
        nullable=False,
        default=0
    )

    total_amount = db.Column(
        db.Float,
        nullable=False,
        default=0
    )

    status = db.Column(
        db.String(20),
        default="発注済"
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.now
    )