import uuid
from datetime import datetime
from sqlalchemy import Column, Date, DateTime, Index, Integer, PrimaryKeyConstraint, String, Text
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

class Activity(Base):
    __tablename__ = "activities"
    __table_args__ = (
        Index("ix_activities_user_id", "user_id"),
        Index("ix_activities_status", "status"),
        Index("ix_activities_user_status", "user_id", "status"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), nullable=False)
    tenant_id = Column(String(36), nullable=False)
    title = Column(String(180), nullable=False)
    description = Column(Text, nullable=False, default="")
    status = Column(String(36), nullable=False, default="todo")
    priority = Column(String(20), nullable=False, default="media")
    due_date = Column(Date, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

class ActivityColumn(Base):
    __tablename__ = "activity_columns"
    __table_args__ = (
        PrimaryKeyConstraint("user_id", "id", name="pk_activity_columns_user_id_id"),
        Index("ix_activity_columns_tenant_user_position", "tenant_id", "user_id", "position"),
    )

    id = Column(String(36), nullable=False)
    user_id = Column(String(36), nullable=False)
    tenant_id = Column(String(36), nullable=False)
    title = Column(String(80), nullable=False)
    color = Column(String(7), nullable=False, default="#087E96")
    position = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
