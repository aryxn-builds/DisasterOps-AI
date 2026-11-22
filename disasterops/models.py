from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def now() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return str(uuid4())


class Base(DeclarativeBase):
    pass


class Account(Base):
    __tablename__ = "accounts"
    __table_args__ = (
        CheckConstraint(
            "role IN ('citizen','dispatcher','responder')", name="account_role"
        ),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    username: Mapped[str] = mapped_column(String(40), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(16), default="citizen")
    phone: Mapped[str | None] = mapped_column(String(16))


class LoginSession(Base):
    __tablename__ = "login_sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    account_id: Mapped[str] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), index=True
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class CitizenSafety(Base):
    __tablename__ = "citizen_safety"
    __table_args__ = (
        CheckConstraint(
            "status IN ('SAFE','NEEDS_HELP')", name="citizen_safety_status"
        ),
    )
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), primary_key=True)
    status: Mapped[str] = mapped_column(String(16))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class SOSReport(Base):
    __tablename__ = "sos_reports"
    __table_args__ = (
        UniqueConstraint("account_id", "client_request_id", name="sos_client_request"),
        UniqueConstraint("gateway_event_id", name="sos_gateway_event"),
        CheckConstraint(
            "(latitude IS NULL AND longitude IS NULL) OR "
            "(latitude IS NOT NULL AND longitude IS NOT NULL AND "
            "latitude BETWEEN -90 AND 90 AND longitude BETWEEN -180 AND 180)",
            name="sos_coordinate_pair",
        ),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    account_id: Mapped[str | None] = mapped_column(
        ForeignKey("accounts.id"), index=True
    )
    client_request_id: Mapped[str | None] = mapped_column(String(36))
    gateway_event_id: Mapped[str | None] = mapped_column(String(128))
    phone: Mapped[str | None] = mapped_column(String(32))
    source: Mapped[str] = mapped_column(String(20))
    message: Mapped[str | None] = mapped_column(Text)
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    accuracy_meters: Mapped[float | None] = mapped_column(Float)
    battery_percentage: Mapped[int | None]
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now, index=True
    )


class Incident(Base):
    __tablename__ = "incidents"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    report_id: Mapped[str] = mapped_column(ForeignKey("sos_reports.id"), unique=True)
    opened_by: Mapped[str] = mapped_column(ForeignKey("accounts.id"))
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class RescueAssignment(Base):
    __tablename__ = "rescue_assignments"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    incident_id: Mapped[str] = mapped_column(ForeignKey("incidents.id"), unique=True)
    responder_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), index=True)
    assigned_by: Mapped[str] = mapped_column(ForeignKey("accounts.id"))
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class LocationRequest(Base):
    __tablename__ = "location_requests"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    report_id: Mapped[str] = mapped_column(ForeignKey("sos_reports.id"), index=True)
    requested_by: Mapped[str] = mapped_column(ForeignKey("accounts.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    accuracy_meters: Mapped[float | None] = mapped_column(Float)
