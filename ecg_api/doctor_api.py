from __future__ import annotations

import os
import io
import datetime
from typing import Optional, List

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ecg_storage.db import get_session, AnalysisResult
from ecg_storage.models import Doctor, Patient, DoctorAnalysisLink
from twilio.rest import Client as TwilioClient
import smtplib
from email.mime.text import MIMEText

AUTH_SECRET = os.getenv("AUTH_SECRET", "dev-secret-change-me")
AUTH_ALGO = "HS256"


# --- Auth helpers (kept local to avoid circular imports) ---
def _extract_bearer_token(request: Request) -> Optional[str]:
    auth = request.headers.get("Authorization")
    if auth and auth.lower().startswith("bearer "):
        return auth.split(" ", 1)[1].strip()
    return None


def get_current_claims(request: Request) -> dict:
    token = _extract_bearer_token(request) or request.query_params.get("token")
    if not token:
        raise HTTPException(status_code=401, detail="Missing token")
    try:
        return jwt.decode(token, AUTH_SECRET, algorithms=[AUTH_ALGO])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def require_doctor(claims: dict = Depends(get_current_claims)):
    if claims.get("role") != "doctor":
        raise HTTPException(status_code=403, detail="Forbidden: doctor role required")
    return claims


router = APIRouter(prefix="/doctor", tags=["doctor"])


# --- Schemas ---
class DoctorProfileIn(BaseModel):
    name: str
    email: str
    specialty: Optional[str] = None
    license_number: Optional[str] = None
    organization: Optional[str] = None
    profile_image_b64: Optional[str] = None


class PatientIn(BaseModel):
    name: str
    email: Optional[str] = None
    identifier: Optional[str] = None
    dob: Optional[str] = None


class AlertSettingsIn(BaseModel):
    whatsapp_enabled: Optional[bool] = None
    whatsapp_to: Optional[str] = None
    email_enabled: Optional[bool] = None
    email_to: Optional[str] = None
    thresholds: Optional[dict] = None  # e.g., {"SDNN": 50, "RMSSD": 20}


@router.get("/me")
def get_my_profile(db: Session = Depends(get_session), claims: dict = Depends(require_doctor)):
    doc = db.query(Doctor).filter(Doctor.user_id == claims.get("uid")).first()
    if not doc:
        # Create minimal record derived from auth if missing
        doc = Doctor(user_id=claims.get("uid"), name=claims.get("sub") or "Doctor", email="")
        db.add(doc)
        db.commit()
        db.refresh(doc)
    return {
        "id": doc.id,
        "name": doc.name,
        "email": doc.email,
        "specialty": doc.specialty,
        "license_number": doc.license_number,
        "organization": doc.organization,
        "profile_image_b64": doc.profile_image,
        "created_at": doc.created_at.isoformat(),
        "settings": doc.settings or {},
    }


@router.patch("/me")
def update_my_profile(payload: DoctorProfileIn, db: Session = Depends(get_session), claims: dict = Depends(require_doctor)):
    doc = db.query(Doctor).filter(Doctor.user_id == claims.get("uid")).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Profile not found")
    doc.name = payload.name
    doc.email = payload.email
    doc.specialty = payload.specialty
    doc.license_number = payload.license_number
    doc.organization = payload.organization
    if payload.profile_image_b64 is not None:
        doc.profile_image = payload.profile_image_b64
    db.add(doc)
    db.commit()
    return {"ok": True}


class LinkAnalysisIn(BaseModel):
    analysis_id: int
    patient_id: int


@router.post("/link-analysis")
def link_analysis(body: LinkAnalysisIn, db: Session = Depends(get_session), claims: dict = Depends(require_doctor)):
    doc = db.query(Doctor).filter(Doctor.user_id == claims.get("uid")).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Profile not found")
    # Validate existence
    ar = db.query(AnalysisResult).filter(AnalysisResult.id == body.analysis_id).first()
    p = db.query(Patient).filter(Patient.id == body.patient_id, Patient.doctor_id == doc.id).first()
    if not ar or not p:
        raise HTTPException(status_code=404, detail="Analysis or patient not found")
    # Check existing
    exists = db.query(DoctorAnalysisLink).filter(DoctorAnalysisLink.analysis_id == body.analysis_id, DoctorAnalysisLink.doctor_id == doc.id).first()
    if exists:
        # Update patient association if different
        exists.patient_id = body.patient_id
        db.add(exists)
        db.commit()
        return {"ok": True, "link_id": exists.id}
    link = DoctorAnalysisLink(doctor_id=doc.id, patient_id=body.patient_id, analysis_id=body.analysis_id)
    db.add(link)
    db.commit()
    db.refresh(link)
    return {"ok": True, "link_id": link.id}


@router.get("/patients")
def list_patients(db: Session = Depends(get_session), claims: dict = Depends(require_doctor)):
    doc = db.query(Doctor).filter(Doctor.user_id == claims.get("uid")).first()
    if not doc:
        return []
    rows = db.query(Patient).filter(Patient.doctor_id == doc.id).order_by(Patient.id.asc()).all()
    return [
        {"id": r.id, "name": r.name, "email": r.email, "identifier": r.identifier, "dob": r.dob}
        for r in rows
    ]


@router.post("/patients")
def create_patient(body: PatientIn, db: Session = Depends(get_session), claims: dict = Depends(require_doctor)):
    doc = db.query(Doctor).filter(Doctor.user_id == claims.get("uid")).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Profile not found")
    p = Patient(doctor_id=doc.id, name=body.name, email=body.email, identifier=body.identifier, dob=body.dob)
    db.add(p)
    db.commit()
    db.refresh(p)
    return {"id": p.id}


@router.patch("/patients/{patient_id}")
def patch_patient(patient_id: int, body: PatientIn, db: Session = Depends(get_session), claims: dict = Depends(require_doctor)):
    doc = db.query(Doctor).filter(Doctor.user_id == claims.get("uid")).first()
    p = db.query(Patient).filter(Patient.id == patient_id, Patient.doctor_id == doc.id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Patient not found")
    p.name = body.name or p.name
    p.email = body.email
    p.identifier = body.identifier
    p.dob = body.dob
    db.add(p)
    db.commit()
    return {"ok": True}


@router.delete("/patients/{patient_id}")
def delete_patient(patient_id: int, db: Session = Depends(get_session), claims: dict = Depends(require_doctor)):
    doc = db.query(Doctor).filter(Doctor.user_id == claims.get("uid")).first()
    p = db.query(Patient).filter(Patient.id == patient_id, Patient.doctor_id == doc.id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Patient not found")
    db.delete(p)
    db.commit()
    return {"ok": True}


class AnalysisQuery(BaseModel):
    patient_id: Optional[int] = None
    abnormal: Optional[bool] = None
    metric: Optional[str] = "SDNN"
    op: Optional[str] = "lt"  # lt/gt
    threshold: Optional[float] = 50.0
    limit: Optional[int] = 200


@router.post("/analyses")
def list_analyses(q: AnalysisQuery, db: Session = Depends(get_session), claims: dict = Depends(require_doctor)):
    doc = db.query(Doctor).filter(Doctor.user_id == claims.get("uid")).first()
    if not doc:
        return []
    # Join via link table
    query = (
        db.query(AnalysisResult, DoctorAnalysisLink)
        .join(DoctorAnalysisLink, DoctorAnalysisLink.analysis_id == AnalysisResult.id)
        .filter(DoctorAnalysisLink.doctor_id == doc.id)
    )
    if q.patient_id:
        query = query.filter(DoctorAnalysisLink.patient_id == q.patient_id)
    rows = query.order_by(AnalysisResult.id.desc()).limit(q.limit or 200).all()

    results = []
    for ar, link in rows:
        hrv = ar.hrv or {}
        ok = True
        if q.abnormal:
            # Simple filter based on time metrics
            t = hrv.get("time", {})
            val = t.get(q.metric or "SDNN")
            if val is None:
                ok = False
            else:
                if (q.op or "lt") == "lt":
                    ok = val < (q.threshold or 0)
                else:
                    ok = val > (q.threshold or 0)
        if ok:
            results.append({
                "analysis_id": ar.id,
                "timestamp": ar.timestamp.isoformat() if ar.timestamp else None,
                "hrv": hrv,
                "quality": ar.quality,
                "ml": ar.ml,
                "patient_id": link.patient_id,
            })
    return results


class FeedbackIn(BaseModel):
    label: str
    notes: Optional[dict] = None


@router.post("/feedback/{analysis_id}")
def add_feedback(analysis_id: int, body: FeedbackIn, db: Session = Depends(get_session), claims: dict = Depends(require_doctor)):
    # Ensure the analysis belongs to this doctor via link table
    doc = db.query(Doctor).filter(Doctor.user_id == claims.get("uid")).first()
    link = db.query(DoctorAnalysisLink).filter(DoctorAnalysisLink.analysis_id == analysis_id, DoctorAnalysisLink.doctor_id == doc.id).first()
    if not link:
        raise HTTPException(status_code=404, detail="Analysis not found for this doctor")
    row = db.query(AnalysisResult).filter(AnalysisResult.id == analysis_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Analysis not found")
    fb = {"label": body.label, "notes": body.notes or {}, "by_uid": claims.get("uid"), "ts": datetime.datetime.utcnow().isoformat()}
    row.feedback = fb
    db.add(row)
    db.commit()
    return {"ok": True}


@router.get("/settings/alerts")
def get_alert_settings(db: Session = Depends(get_session), claims: dict = Depends(require_doctor)):
    doc = db.query(Doctor).filter(Doctor.user_id == claims.get("uid")).first()
    return (doc.settings or {}).get("alerts", {}) if doc else {}


@router.post("/settings/alerts")
def set_alert_settings(body: AlertSettingsIn, db: Session = Depends(get_session), claims: dict = Depends(require_doctor)):
    doc = db.query(Doctor).filter(Doctor.user_id == claims.get("uid")).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Profile not found")
    s = doc.settings or {}
    s_alerts = s.get("alerts", {})
    if body.whatsapp_enabled is not None:
        s_alerts["whatsapp_enabled"] = bool(body.whatsapp_enabled)
    if body.whatsapp_to is not None:
        s_alerts["whatsapp_to"] = (body.whatsapp_to or "").strip() or None
    if body.email_enabled is not None:
        s_alerts["email_enabled"] = bool(body.email_enabled)
    if body.email_to is not None:
        s_alerts["email_to"] = (body.email_to or "").strip() or None
    if body.thresholds is not None:
        s_alerts["thresholds"] = body.thresholds
    s["alerts"] = s_alerts
    doc.settings = s
    db.add(doc)
    db.commit()
    return {"ok": True}


@router.post("/notifications/test")
def test_notification(db: Session = Depends(get_session), claims: dict = Depends(require_doctor)):
    doc = db.query(Doctor).filter(Doctor.user_id == claims.get("uid")).first()
    s = (doc.settings or {}).get("alerts", {}) if doc else {}
    to = s.get("whatsapp_to")
    enabled = s.get("whatsapp_enabled")
    result = {"ok": True}
    # WhatsApp
    if to and enabled:
        from_num = os.getenv("TWILIO_WHATSAPP_FROM")
        sid = os.getenv("TWILIO_SID")
        token = os.getenv("TWILIO_TOKEN")
        key_sid = os.getenv("TWILIO_API_KEY_SID")
        key_secret = os.getenv("TWILIO_API_KEY_SECRET")
        if from_num:
            try:
                if key_sid and key_secret:
                    client = TwilioClient(key_sid, key_secret)
                elif sid and token:
                    client = TwilioClient(sid, token)
                else:
                    result["whatsapp"] = "Credenciales Twilio no configuradas"
                if 'client' in locals():
                    res = client.messages.create(
                        from_=from_num,
                        to=to,
                        body=f"[TEST] Notificación WhatsApp para {doc.name} ({datetime.datetime.utcnow().isoformat()})"
                    )
                    result["whatsapp_sid"] = res.sid
            except Exception as e:
                result["whatsapp_error"] = str(e)
        else:
            result["whatsapp"] = "TWILIO_WHATSAPP_FROM no configurado"
    else:
        result["whatsapp"] = "deshabilitado"
    # Email (optional)
    e_enabled = s.get("email_enabled")
    e_to = s.get("email_to")
    if e_enabled and e_to:
        try:
            host = os.getenv("SMTP_HOST")
            port = int(os.getenv("SMTP_PORT", "587"))
            user = os.getenv("SMTP_USER")
            pwd = os.getenv("SMTP_PASS")
            sender = os.getenv("SMTP_FROM", user or "noreply@example.com")
            if not host:
                result["email"] = "SMTP_HOST no configurado"
            else:
                msg = MIMEText(f"Prueba de notificación para {doc.name} a las {datetime.datetime.utcnow().isoformat()}.")
                msg["Subject"] = "ECG - Prueba de notificación"
                msg["From"] = sender
                msg["To"] = e_to
                with smtplib.SMTP(host, port, timeout=20) as server:
                    server.starttls()
                    if user and pwd:
                        server.login(user, pwd)
                    server.sendmail(sender, [e_to], msg.as_string())
                result["email"] = "enviado"
        except Exception as e:
            result["email_error"] = str(e)
    else:
        result["email"] = "deshabilitado"
    return result


# --- Export PDF ---
def _render_pdf(ar: AnalysisResult, patient: Optional[Patient]) -> bytes:
    # Minimal PDF via reportlab (no external binaries)
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4
    y = height - 50
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, "ECG HRV Report")
    y -= 24
    c.setFont("Helvetica", 10)
    if patient:
        c.drawString(50, y, f"Paciente: {patient.name}  ID: {patient.identifier or '-'}  Email: {patient.email or '-'}")
        y -= 18
    ts = ar.timestamp.isoformat() if ar.timestamp else "-"
    c.drawString(50, y, f"Análisis ID: {ar.id}  Fecha: {ts}")
    y -= 18
    # HRV summary
    t = (ar.hrv or {}).get("time", {})
    f = (ar.hrv or {}).get("freq", {})
    c.drawString(50, y, f"SDNN: {t.get('SDNN')}  RMSSD: {t.get('RMSSD')}  pNN50: {t.get('pNN50')}")
    y -= 16
    c.drawString(50, y, f"LF: {f.get('LF')}  HF: {f.get('HF')}  LF/HF: {f.get('LF_HF')}")
    y -= 16
    q = ar.quality or {}
    c.drawString(50, y, f"Calidad: SNR: {q.get('snr_db')} dB  Artefactos: {q.get('artifact_ratio')}")
    y -= 18
    if ar.feedback:
        c.drawString(50, y, f"Diagnóstico: {ar.feedback.get('label')}  Notas: {ar.feedback.get('notes')}")
        y -= 18
    c.showPage()
    c.save()
    return buf.getvalue()


@router.get("/analysis/{analysis_id}/export-pdf")
def export_pdf(analysis_id: int, db: Session = Depends(get_session), claims: dict = Depends(require_doctor)):
    # Ensure ownership
    doc = db.query(Doctor).filter(Doctor.user_id == claims.get("uid")).first()
    link = db.query(DoctorAnalysisLink).filter(DoctorAnalysisLink.analysis_id == analysis_id, DoctorAnalysisLink.doctor_id == doc.id).first()
    if not link:
        raise HTTPException(status_code=404, detail="Analysis not found for this doctor")
    ar = db.query(AnalysisResult).filter(AnalysisResult.id == analysis_id).first()
    patient = db.query(Patient).filter(Patient.id == link.patient_id).first() if link else None
    pdf_bytes = _render_pdf(ar, patient)
    filename = f"hrv_report_{analysis_id}.pdf"
    return StreamingResponse(io.BytesIO(pdf_bytes), media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename={filename}"})
