import sys
import unittest
from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace

SERVICE_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SERVICE_ROOT))

from app.api.schemas.activity_schema import ActivityCreate
from app.application.use_cases.activity_support import activity_column_to_dict, activity_to_dict


class ActivitySchemaTests(unittest.TestCase):
    def test_create_schema_accepts_legacy_column_and_date_aliases(self):
        activity = ActivityCreate.model_validate({
            "title": "Revisar contrato",
            "columnId": "in_progress",
            "due_date": "2026-11-15T10:30:00",
        })
        self.assertEqual(activity.status, "in_progress")
        self.assertEqual(activity.dueDate, date(2026, 11, 15))


class ActivitySerializationTests(unittest.TestCase):
    def test_activity_serialization_keeps_camel_case_response_contract(self):
        now = datetime(2026, 10, 31, 12, 0, 0)
        activity = SimpleNamespace(
            id="activity-1", user_id="user-1", title="Revisar contrato",
            description="", status="todo", priority="media", due_date=None,
            created_at=now, updated_at=now,
        )
        result = activity_to_dict(activity)
        self.assertEqual(result["userId"], "user-1")
        self.assertEqual(result["dueDate"], None)
        self.assertIn("createdAt", result)
        self.assertNotIn("user_id", result)

    def test_column_serialization_keeps_position_and_color(self):
        now = datetime(2026, 10, 31, 12, 0, 0)
        column = SimpleNamespace(
            id="todo", title="A Fazer", color="#087E96", position=0,
            created_at=now, updated_at=now,
        )
        result = activity_column_to_dict(column)
        self.assertEqual(result["position"], 0)
        self.assertEqual(result["color"], "#087E96")
        self.assertIn("updatedAt", result)


if __name__ == "__main__":
    unittest.main()
