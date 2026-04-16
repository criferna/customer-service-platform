"""Modelo SQLAlchemy para la entidad Notification."""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


# ENUMs de PostgreSQL definidos en notifications-init.sql
NotificationChannel = ENUM('EMAIL', 'SMS', 'PUSH', 'INTERNAL', name='notification_channel', create_type=False)
NotificationStatus = ENUM('PENDING', 'SENT', 'FAILED', 'DELIVERED', name='notification_status', create_type=False)
RecipientType = ENUM('CUSTOMER', 'AGENT', name='recipient_type', create_type=False)


class NotificationModel(Base):
    __tablename__ = "notifications"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    recipient_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    recipient_type: Mapped[str] = mapped_column(RecipientType, nullable=False)
    recipient_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    channel: Mapped[str] = mapped_column(NotificationChannel, nullable=False, default="INTERNAL")
    subject: Mapped[str] = mapped_column(String(300), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(NotificationStatus, nullable=False, default="PENDING")
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_event_id: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True), nullable=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
