import unittest

from models.purchase import Purchase


class PurchaseModelTest(unittest.TestCase):
    def test_purchase_has_required_fields(self):
        column_names = {column.name for column in Purchase.__table__.columns}

        self.assertIn("supplier_name", column_names)
        self.assertIn("unit_price", column_names)
        self.assertIn("total_amount", column_names)


if __name__ == "__main__":
    unittest.main()
