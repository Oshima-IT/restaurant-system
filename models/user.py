from models.database import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(
        db.String(50),
        unique=True,
        nullable=False
    )

    password = db.Column(
        db.String(255),
        nullable=False
    )

    name = db.Column(
        db.String(100),
        nullable=False
    )

    role = db.Column(
        db.String(20),
        nullable=False,
        default="admin"
    )

    hourly_wage = db.Column(
        db.Integer,
        nullable=False,
        default=1500
    )

    created_at = db.Column(
        db.DateTime,
        server_default=db.func.now()
    )