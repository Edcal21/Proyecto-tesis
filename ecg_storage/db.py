from __future__ import annotations

import os
from datetime import datetime
from typing import Optional

from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime, JSON, text, UniqueConstraint
from sqlalchemy.orm import declarative_base, sessionmaker


def _get_database_url() -> str:
	# Use env var if provided, else local SQLite file
	url = os.getenv("DATABASE_URL")
	if url:
		return url
	# Default to a local SQLite file in current working directory
	return "sqlite:///ecg.db"


DATABASE_URL = _get_database_url()

# For SQLite, need check_same_thread=False when used with FastAPI/uvicorn
engine = create_engine(
	DATABASE_URL,
	connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
	pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Event(Base):
	__tablename__ = "events"

	id = Column(Integer, primary_key=True, index=True)
	timestamp = Column(DateTime, index=True, nullable=False)
	rr_ms = Column(Float, nullable=True)
	hr_bpm = Column(Float, nullable=True)
	source = Column(String(64), nullable=True)
	extras = Column(JSON, nullable=True)


class Alert(Base):
	__tablename__ = "alerts"

	id = Column(Integer, primary_key=True, index=True)
	timestamp = Column(DateTime, index=True, nullable=False)
	type = Column(String(64), index=True, nullable=False)
	severity = Column(String(32), index=True, nullable=False)
	details = Column(JSON, nullable=True)


class User(Base):
	__tablename__ = "users"
	__table_args__ = (
		UniqueConstraint('username', name='uq_users_username'),
	)

	id = Column(Integer, primary_key=True, index=True)
	username = Column(String(64), nullable=False, index=True)
	password_hash = Column(String(255), nullable=False)
	role = Column(String(32), nullable=False, default="doctor")
	created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class AnalysisResult(Base):
	__tablename__ = "analysis_results"

	id = Column(Integer, primary_key=True, index=True)
	timestamp = Column(DateTime, index=True, nullable=False, default=datetime.utcnow)
	source = Column(String(64), nullable=True)
	# Core payloads
	hrv = Column(JSON, nullable=True)
	ml = Column(JSON, nullable=True)
	quality = Column(JSON, nullable=True)
	extras = Column(JSON, nullable=True)  # pr_intervals, counts, etc.
	# Feedback from doctor
	feedback = Column(JSON, nullable=True)  # {label, notes, by_uid}


class NotificationConfig(Base):
	__tablename__ = "notification_config"

	id = Column(Integer, primary_key=True, index=True)
	whatsapp_enabled = Column(Integer, nullable=False, default=0)  # 0/1
	whatsapp_to = Column(String(32), nullable=True)
	updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)
	updated_by = Column(Integer, nullable=True)  # uid del usuario que actualizó


def init_db() -> None:
	Base.metadata.create_all(bind=engine)


def get_session():
	db = SessionLocal()
	try:
		yield db
	finally:
		db.close()

