import unittest

from app import parse_pos_ocr_result


class PosOcrParserTest(unittest.TestCase):
    def test_extracts_total_and_times(self):
        text = """
        レシート
        合計 12,500円
        11:30
        19:45
        """

        result = parse_pos_ocr_result(text)

        self.assertEqual(result["total_amount"], 12500)
        self.assertEqual(result["clock_in"], "11:30")
        self.assertEqual(result["clock_out"], "19:45")

    def test_falls_back_to_largest_number(self):
        text = """
        最終画面
        3500
        8000
        """

        result = parse_pos_ocr_result(text)

        self.assertEqual(result["total_amount"], 8000)


if __name__ == "__main__":
    unittest.main()
