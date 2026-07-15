import unittest

from app import can_access_route


class RolePermissionTest(unittest.TestCase):
    def test_admin_has_full_access(self):
        self.assertTrue(can_access_route("employees", "admin"))
        self.assertTrue(can_access_route("products", "admin"))
        self.assertTrue(can_access_route("purchase", "admin"))

    def test_manager_has_limited_access(self):
        self.assertTrue(can_access_route("products", "manager"))
        self.assertTrue(can_access_route("purchase", "manager"))
        self.assertFalse(can_access_route("employees", "manager"))

    def test_staff_has_basic_access(self):
        self.assertTrue(can_access_route("pos", "staff"))
        self.assertTrue(can_access_route("dashboard", "staff"))
        self.assertFalse(can_access_route("products", "staff"))


if __name__ == "__main__":
    unittest.main()
