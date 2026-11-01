from datetime import date, timedelta


def due_date_window(days: int, today: date | None = None) -> tuple[str, str]:
    start = today or date.today()
    return start.isoformat(), (start + timedelta(days=days)).isoformat()
