class Config:
    SECRET_KEY = "restaurant_secret_key"

    SQLALCHEMY_DATABASE_URI = (
        "mysql+pymysql://restaurant_user:password123@localhost/restaurant_system"
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False