from app import app, db
from models.sale import Sale
from datetime import datetime, timedelta
import random

def create_mock_data():
    with app.app_context():
        # Clear existing sales if needed
        # Sale.query.delete()
        
        today = datetime.now()
        # Create data for the last 60 days
        for i in range(60):
            target_date = today - timedelta(days=i)
            # Create 3-8 sales per day
            num_sales = random.randint(3, 8)
            for _ in range(num_sales):
                sale = Sale(
                    total_price=random.randint(500, 5000),
                    created_at=target_date.replace(hour=random.randint(9, 21), minute=random.randint(0, 59))
                )
                db.session.add(sale)
        
        db.session.commit()
        print("Mock data created successfully.")

if __name__ == "__main__":
    create_mock_data()
