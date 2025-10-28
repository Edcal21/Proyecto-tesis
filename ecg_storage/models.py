from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship

from .db import Base


class Doctor(Base):
    __tablename__ = "doctors"

    id = Column(Integer, primary_key=True, index=True)
    # Link to auth user (users.id). One-to-one mapping assumed.
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)

    name = Column(String(128), nullable=False)
    email = Column(String(128), nullable=False)
    password_hash = Column(String(255), nullable=True)  # optional: may rely on User
    specialty = Column(String(64), nullable=True)
    license_number = Column(String(64), nullable=True)
    organization = Column(String(128), nullable=True)
    profile_image = Column(Text, nullable=True)  # base64-encoded image or URL
    settings = Column(JSON, nullable=True)  # per-doctor settings (alerts, notifications)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    patients = relationship("Patient", back_populates="doctor", cascade="all, delete-orphan")


class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=False, index=True)

    name = Column(String(128), nullable=False)
    email = Column(String(128), nullable=True)
    identifier = Column(String(64), nullable=True)  # MRN or other identifier
    dob = Column(String(16), nullable=True)  # ISO date string for simplicity
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    doctor = relationship("Doctor", back_populates="patients")


class DoctorAnalysisLink(Base):
    __tablename__ = "doctor_analysis_link"

    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)
    analysis_id = Column(Integer, ForeignKey("analysis_results.id"), nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
