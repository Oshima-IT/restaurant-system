import unittest

from app import calculate_financial_summary


class FinancialSummaryTest(unittest.TestCase):
    def test_summary_includes_labor_and_cogs(self):
        summary = calculate_financial_summary(total_sales=100000, sale_count=10)

        self.assertEqual(summary["labor_cost"], 37500)
        self.assertEqual(summary["cogs"], 35000)
        self.assertEqual(summary["gross_profit"], 27500)
        self.assertEqual(summary["gross_margin_rate"], 27.5)


if __name__ == "__main__":
    unittest.main()
