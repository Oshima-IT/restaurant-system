import unittest

from models.user import User


class UserModelTest(unittest.TestCase):
    def test_user_has_hourly_wage_field(self):
        column_names = {column.name for column in User.__table__.columns}
        self.assertIn("hourly_wage", column_names)


if __name__ == "__main__":
    unittest.main()
