from datetime import datetime
from sqlalchemy.orm import Session
from app.infrastructure.database.models.activity_model import Activity, ActivityColumn

DEFAULT_ACTIVITY_COLUMNS = [
    {"id": "todo", "title": "A Fazer", "color": "#087E96"},
    {"id": "in_progress", "title": "Em Andamento", "color": "#D97706"},
    {"id": "done", "title": "Concluído", "color": "#16834F"},
]

def activity_column_to_dict(column: ActivityColumn):
    return {
        "id": column.id, "title": column.title, "color": column.color,
        "position": column.position, "createdAt": column.created_at.isoformat(),
        "updatedAt": column.updated_at.isoformat(),
    }

def ensure_activity_columns(db: Session, user_id: str, tenant_id: str):
    columns = db.query(ActivityColumn).filter_by(user_id=user_id, tenant_id=tenant_id).order_by(ActivityColumn.position).all()
    if columns:
        return columns
    now = datetime.utcnow()
    columns = [ActivityColumn(**definition, user_id=user_id, tenant_id=tenant_id, position=index, created_at=now, updated_at=now)
               for index, definition in enumerate(DEFAULT_ACTIVITY_COLUMNS)]
    db.add_all(columns)
    db.commit()
    return db.query(ActivityColumn).filter_by(user_id=user_id, tenant_id=tenant_id).order_by(ActivityColumn.position).all()

def activity_to_dict(activity: Activity):
    return {
        "id": activity.id,
        "userId": activity.user_id,
        "title": activity.title,
        "description": activity.description,
        "status": activity.status,
        "priority": activity.priority,
        "dueDate": activity.due_date.isoformat() if activity.due_date else None,
        "createdAt": activity.created_at.isoformat(),
        "updatedAt": activity.updated_at.isoformat(),
    }
