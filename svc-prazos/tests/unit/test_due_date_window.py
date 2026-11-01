import unittest
from datetime import date

from app.application.use_cases.due_date_window import due_date_window


class DueDateWindowTests(unittest.TestCase):
    def test_window_uses_requested_day_count(self):
        start, end = due_date_window(7, today=date(2026, 2, 10))

        self.assertEqual(start, "2026-02-10")
        self.assertEqual(end, "2026-02-17")
