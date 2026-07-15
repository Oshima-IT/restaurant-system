from models.database import db
from datetime import datetime

class Attendance(db.Model):

    __tablename__ = "attendance"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        nullable=False
    )

    work_date = db.Column(
        db.Date,
        nullable=False
    )

    clock_in = db.Column(
        db.DateTime
    )

    clock_out = db.Column(
        db.DateTime
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.now
    )