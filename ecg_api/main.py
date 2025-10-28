from fastapi import FastAPI, WebSocket, HTTPException, Depends, Request
from pydantic import BaseModel
import asyncio
import numpy as np
from ecg_processing.p_wave import detect_p_waves
from ecg_processing.t_wave import detect_t_waves
from ecg_processing.hrv import compute_hrv
from ecg_processing.intervals import compute_intervals
from ecg_processing.filters import estimate_quality
from ecg_ml.classifier import get_classifier
from ecg_ml.hf_loader import get_ecg2hrv_model, run_ecg2hrv
from typing import Optional
from twilio.rest import Client as TwilioClient
from sqlalchemy.orm import Session
from ecg_storage.db import init_db, get_session, Event, Alert, User, AnalysisResult, NotificationConfig
import ecg_storage.models  # ensure models are registered with Base before init_db
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
import datetime
import jwt
try:
    # Import condicional: en Raspberry Pi estará disponible
    from ecg_hardware.ads1115 import stream_samples
    HAS_ADS = True
except Exception:
    HAS_ADS = False

load_dotenv()  # Cargar variables desde .env si existe

app = FastAPI()

# CORS: permite cualquier origen (React en cualquier puerto)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Config JWT
AUTH_SECRET = os.getenv("AUTH_SECRET", "dev-secret-change-me")
AUTH_ALGO = "HS256"
AUTH_EXP_HOURS = float(os.getenv("AUTH_EXP_HOURS", "8"))
TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_TOKEN = os.getenv("TWILIO_TOKEN")
TWILIO_API_KEY_SID = os.getenv("TWILIO_API_KEY_SID")
TWILIO_API_KEY_SECRET = os.getenv("TWILIO_API_KEY_SECRET")
TWILIO_WHATSAPP_FROM = os.getenv("TWILIO_WHATSAPP_FROM")  # e.g., 'whatsapp:+14155238886'
ALERT_WHATSAPP_TO = os.getenv("ALERT_WHATSAPP_TO")        # e.g., 'whatsapp:+52155...'
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")
ADMIN_WHATSAPP = os.getenv("ADMIN_WHATSAPP")

# --- Auth helpers (RBAC) ---
def decode_token(token: str) -> dict:
    return jwt.decode(token, AUTH_SECRET, algorithms=[AUTH_ALGO])

def _extract_bearer_token(request: Request) -> str | None:
    auth = request.headers.get("Authorization")
    if auth and auth.lower().startswith("bearer "):
        return auth.split(" ", 1)[1].strip()
    return None

def get_current_claims(request: Request) -> dict:
    # Allow token via Authorization header or query param ?token=
    token = _extract_bearer_token(request) or request.query_params.get("token")
    if not token:
        raise HTTPException(status_code=401, detail="Missing token")
    try:
        return decode_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

def require_roles(*roles: str):
    def _dep(claims: dict = Depends(get_current_claims)):
        role = claims.get("role")
        if roles and role not in roles:
            raise HTTPException(status_code=403, detail="Forbidden: insufficient role")
        return claims
    return _dep

# Initialize DB on startup
@app.on_event("startup")
def _startup():
    init_db()


@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/")
def root():
    return {
        "service": "ECG API",
        "status": "ok",
        "endpoints": [
            "/health",
            "/auth/login",
            "/auth/verify",
            "/events",
            "/alerts",
            "/analysis",
            "/ws/ecg",
            "/docs",
        ],
        "docs": "/docs"
    }

@app.websocket("/ws/ecg")
async def ecg_stream(websocket: WebSocket):
    # Validate JWT from query param for WebSocket (e.g., ws://.../ws/ecg?token=...)
    token = websocket.query_params.get("token")
    await websocket.accept()
    try:
        if not token:
            await websocket.close(code=4401)
            return
        try:
            claims = decode_token(token)
        except jwt.ExpiredSignatureError:
            await websocket.close(code=4401)
            return
        except jwt.InvalidTokenError:
            await websocket.close(code=4401)
            return
        if claims.get("role") != "doctor":
            await websocket.close(code=4403)
            return
        if HAS_ADS:
            # Transmitir muestras reales desde ADS1115
            for s in stream_samples(rate=250):  # ajusta address/channel según tu wiring
                await websocket.send_json({
                    "timestamp": s["timestamp"],
                    "voltage_mV": s["voltage_mV"],
                })
                # cede control al loop
                await asyncio.sleep(0)
        else:
            # Fallback: simulación (25 Hz)
            import random, datetime
            while True:
                data = {
                    "timestamp": datetime.datetime.utcnow().isoformat(),
                    "voltage_mV": random.uniform(-1, 1)
                }
                await websocket.send_json(data)
                await asyncio.sleep(0.04)
    except Exception:
        await websocket.close()


class AnalysisRequest(BaseModel):
    signal: list  # lista de valores de la señal (mV)
    fs: float     # frecuencia de muestreo (Hz)
    persist: bool = False  # si se deben guardar eventos/alertas
def _detect_alerts(rr_ms: np.ndarray, pr_ms: list[float]) -> list[dict]:
    alerts = []
    # Simple AF heuristic: high RR variability and absence of P (handled upstream)
    if len(rr_ms) >= 4:
        sdnn = float(np.std(rr_ms))
        if sdnn > 120:  # ms threshold
            alerts.append({"type": "AF_suspected", "severity": "warning", "details": {"sdnn_ms": sdnn}})
    # Simple AV block heuristic: prolonged PR intervals
    long_pr = [x for x in pr_ms if x and x > 200]
    if len(long_pr) >= 3:
        alerts.append({"type": "AV_block_suspected", "severity": "warning", "details": {"n_long_pr": len(long_pr)}})
    return alerts

def _hrv_alerts(hrv: dict) -> list[dict]:
    alerts = []
    t = (hrv or {}).get('time', {})
    f = (hrv or {}).get('freq', {})
    sdnn = t.get('SDNN')
    rmssd = t.get('RMSSD')
    pnn50 = t.get('pNN50')
    lf_hf = f.get('LF_HF')
    # Umbrales simples (ajustables): SDNN bajo, LF/HF alto o bajo, pNN50 bajo
    if sdnn is not None and not np.isnan(sdnn) and sdnn < 50:
        alerts.append({"type": "HRV_low_SDNN", "severity": "warning", "details": {"sdnn": sdnn}})
    if rmssd is not None and not np.isnan(rmssd) and rmssd < 20:
        alerts.append({"type": "HRV_low_RMSSD", "severity": "warning", "details": {"rmssd": rmssd}})
    if pnn50 is not None and not np.isnan(pnn50) and pnn50 < 5:
        alerts.append({"type": "HRV_low_pNN50", "severity": "info", "details": {"pnn50": pnn50}})
    if lf_hf is not None and not np.isnan(lf_hf) and (lf_hf > 3 or lf_hf < 0.5):
        alerts.append({"type": "HRV_abnormal_LF_HF", "severity": "warning", "details": {"lf_hf": lf_hf}})
    return alerts

def _send_whatsapp(msg: str) -> Optional[str]:
    dest = ADMIN_WHATSAPP or ALERT_WHATSAPP_TO
    if not (TWILIO_WHATSAPP_FROM and dest):
        return None
    try:
        if TWILIO_API_KEY_SID and TWILIO_API_KEY_SECRET:
            client = TwilioClient(TWILIO_API_KEY_SID, TWILIO_API_KEY_SECRET)
        elif TWILIO_SID and TWILIO_TOKEN:
            client = TwilioClient(TWILIO_SID, TWILIO_TOKEN)
        else:
            return None
        # Normaliza destino para WhatsApp
        to = dest.strip()
        to = to.replace(" ", "")
        if not to.startswith("whatsapp:"):
            if not to.startswith("+"):
                # Si no incluye +, se deja tal cual; Twilio requiere E.164.
                pass
            to = f"whatsapp:{to}"
        res = client.messages.create(
            from_=TWILIO_WHATSAPP_FROM,
            to=to,
            body=msg
        )
        return res.sid
    except Exception:
        return None


@app.post("/analysis")
def advanced_analysis(req: AnalysisRequest, db: Session = Depends(get_session), claims: dict = Depends(require_roles("doctor"))):
    """
    Endpoint para análisis avanzado de ECG: ondas P, T, HRV, intervalos.
    """
    sig = np.array(req.signal)
    fs = req.fs
    # Detectar ondas
    p_peaks = detect_p_waves(sig, fs)
    t_peaks = detect_t_waves(sig, fs)
    # Simular R-peaks (en producción usa tu algoritmo QRS)
    from scipy.signal import find_peaks
    r_peaks, _ = find_peaks(sig, distance=int(0.6*fs), prominence=0.2)
    # RR intervals
    rr_intervals = np.diff(r_peaks) / fs * 1000  # ms
    hrv_metrics = compute_hrv(rr_intervals)
    # Intervalos PR (ejemplo)
    pr_intervals = compute_intervals(r_peaks, p_peaks, t_peaks, fs)
    clf = get_classifier()
    ml_pred = clf.predict(sig, fs)

    # HF model (ECG2HRV) integration (best-effort)
    try:
        ecg2hrv = get_ecg2hrv_model()
        if ecg2hrv is not None:
            hf_out = run_ecg2hrv(ecg2hrv, sig, fs)
        else:
            hf_out = {"ok": False, "error": "Modelo no disponible"}
    except Exception as _:
        hf_out = {"ok": False, "error": "Fallo al ejecutar modelo"}

    quality = estimate_quality(sig, fs)

    result = {
        "n_p_peaks": int(len(p_peaks)),
        "n_t_peaks": int(len(t_peaks)),
        "n_r_peaks": int(len(r_peaks)),
        "hrv": hrv_metrics,
    "ml": ml_pred,
    "hf_model": hf_out,
        "quality": quality,
        "pr_intervals_ms": pr_intervals
    }

    # Build events (RR/HR) and alerts
    if len(rr_intervals) > 0:
        hr_bpm_seq = 60000.0 / rr_intervals
        result["rr_ms"] = rr_intervals.tolist()
        result["hr_bpm_seq"] = hr_bpm_seq.tolist()
        alerts = _detect_alerts(rr_intervals, pr_intervals)
        # Agregar alertas basadas en HRV
        alerts += _hrv_alerts(hrv_metrics)
        result["alerts"] = alerts

        if req.persist:
            # Persist events
            now = None
            for i, rr in enumerate(rr_intervals):
                ev = Event(timestamp=np.datetime64('now').astype('datetime64[ms]').astype(object), rr_ms=float(rr), hr_bpm=float(hr_bpm_seq[i]), source="analysis", extras=None)
                db.add(ev)
            # Persist alerts
            # Verificar configuración de notificaciones
            cfg = db.query(NotificationConfig).first()
            wp_enabled = bool(cfg and cfg.whatsapp_enabled)
            wp_to_override = cfg.whatsapp_to if cfg and cfg.whatsapp_to else None

            for a in alerts:
                al = Alert(timestamp=np.datetime64('now').astype('datetime64[ms]').astype(object), type=a["type"], severity=a["severity"], details=a.get("details"))
                db.add(al)
                # Notificación WhatsApp (mejor: throttle y desduplicación en producción)
                if wp_enabled:
                    if wp_to_override:
                        # Override destino temporalmente usando variable de proceso
                        os.environ['ALERT_WHATSAPP_TO'] = wp_to_override
                    _send_whatsapp(f"[ALERTA HRV] {a['type']} ({a['severity']}) detalles: {a.get('details')}")
            db.commit()

    if req.persist:
        row = AnalysisResult(
            source="analysis",
            hrv=hrv_metrics,
            ml=ml_pred,
            quality=quality,
            extras={
                "n_p_peaks": int(len(p_peaks)),
                "n_t_peaks": int(len(t_peaks)),
                "n_r_peaks": int(len(r_peaks)),
                "pr_intervals_ms": pr_intervals,
            },
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        result["analysis_id"] = row.id
    return result


class FeedbackIn(BaseModel):
    label: str
    notes: dict | None = None


@app.post("/analysis/{analysis_id}/feedback")
def post_feedback(analysis_id: int, body: FeedbackIn, db: Session = Depends(get_session), claims: dict = Depends(require_roles("doctor","admin"))):
    row = db.query(AnalysisResult).filter(AnalysisResult.id == analysis_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Analysis not found")
    fb = {"label": body.label, "notes": body.notes or {}, "by_uid": claims.get("uid"), "ts": datetime.datetime.utcnow().isoformat()}
    row.feedback = fb
    db.add(row)
    db.commit()
    return {"ok": True, "analysis_id": analysis_id, "feedback": fb}


# --- Notification settings (admin only) ---
class NotificationBody(BaseModel):
    whatsapp_enabled: bool
    whatsapp_to: str | None = None


@app.get("/admin/notifications")
def get_notifications(db: Session = Depends(get_session), claims: dict = Depends(require_roles("admin"))):
    cfg = db.query(NotificationConfig).first()
    return {
        "whatsapp_enabled": bool(cfg.whatsapp_enabled) if cfg else False,
        "whatsapp_to": cfg.whatsapp_to if cfg else None,
    }


@app.post("/admin/notifications")
def set_notifications(body: NotificationBody, db: Session = Depends(get_session), claims: dict = Depends(require_roles("admin"))):
    cfg = db.query(NotificationConfig).first()
    if not cfg:
        cfg = NotificationConfig()
    cfg.whatsapp_enabled = 1 if body.whatsapp_enabled else 0
    cfg.whatsapp_to = (body.whatsapp_to or '').strip() or None
    cfg.updated_by = claims.get("uid")
    cfg.updated_at = datetime.datetime.utcnow()
    db.add(cfg)
    db.commit()
    return {"ok": True}


@app.post("/admin/test-whatsapp")
def admin_test_whatsapp(claims: dict = Depends(require_roles("admin"))):
    ts = datetime.datetime.utcnow().isoformat()
    sid = _send_whatsapp(f"[TEST] Notificación WhatsApp desde ECG API a las {ts}")
    if sid:
        return {"ok": True, "sid": sid}
    return {"ok": False, "message": "WhatsApp no configurado o fallo de envío"}


class EventsIn(BaseModel):
    events: list[dict]


@app.post("/events")
def create_events(payload: EventsIn, db: Session = Depends(get_session), claims: dict = Depends(require_roles("doctor"))):
    for e in payload.events:
        ev = Event(
            timestamp=np.datetime64(e.get("timestamp", 'now')).astype('datetime64[ms]').astype(object),
            rr_ms=e.get("rr_ms"),
            hr_bpm=e.get("hr_bpm"),
            source=e.get("source"),
            extras=e.get("extras"),
        )
        db.add(ev)
    db.commit()
    return {"inserted": len(payload.events)}


@app.get("/events")
def list_events(limit: int = 200, db: Session = Depends(get_session), claims: dict = Depends(require_roles("doctor"))):
    rows = db.query(Event).order_by(Event.id.desc()).limit(limit).all()
    return [
        {"id": r.id, "timestamp": r.timestamp.isoformat(), "rr_ms": r.rr_ms, "hr_bpm": r.hr_bpm, "source": r.source, "extras": r.extras}
        for r in rows
    ]


class AlertIn(BaseModel):
    type: str
    severity: str = "info"
    details: dict | None = None


@app.post("/alerts")
def create_alert(alert: AlertIn, db: Session = Depends(get_session), claims: dict = Depends(require_roles("doctor"))):
    row = Alert(timestamp=np.datetime64('now').astype('datetime64[ms]').astype(object), type=alert.type, severity=alert.severity, details=alert.details)
    db.add(row)
    db.commit()
    return {"id": row.id}


@app.get("/alerts")
def list_alerts(limit: int = 200, db: Session = Depends(get_session), claims: dict = Depends(require_roles("doctor"))):
    rows = db.query(Alert).order_by(Alert.id.desc()).limit(limit).all()
    return [
        {"id": r.id, "timestamp": r.timestamp.isoformat(), "type": r.type, "severity": r.severity, "details": r.details}
        for r in rows
    ]


# --- AUTH endpoints para integrar login React ---
class LoginRequest(BaseModel):
    username: str
    password: str


# Use bcrypt_sha256 to avoid 72-byte password edge cases and backend quirks
from passlib.hash import bcrypt_sha256 as pwd_hash


# --- Support: Request access (no auth required) ---
class SupportAccessRequest(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    note: Optional[str] = None
    user_agent: Optional[str] = None


@app.post("/support/request-access")
def support_request_access(body: SupportAccessRequest, request: Request):
    """
    Receives an access request and notifies the administrator via WhatsApp if configured.
    Always returns 200 with basic info, even if delivery is not configured.
    """
    ua = request.headers.get("User-Agent")
    msg = (
        "[ACCESS REQUEST]\n"
        f"username: {body.username or '-'}\n"
        f"email: {body.email or '-'}\n"
        f"note: {body.note or '-'}\n"
        f"user_agent: {body.user_agent or ua or '-'}\n"
        f"time: {datetime.datetime.utcnow().isoformat()}Z\n"
    )
    sid = _send_whatsapp(msg)
    delivered_via = "whatsapp" if sid else "none"
    return {
        "ok": True,
        "delivered_via": delivered_via,
        "twilio_sid": sid,
        "admin": {
            "email": ADMIN_EMAIL,
            "whatsapp": ADMIN_WHATSAPP or ALERT_WHATSAPP_TO,
        },
    }


@app.post("/auth/login")
def auth_login(req: LoginRequest, db: Session = Depends(get_session)):
    # Buscar usuario en DB
    user = db.query(User).filter(User.username == req.username).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    # Validar contraseña
    if not pwd_hash.verify(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    payload = {
        "sub": user.username,
        "uid": user.id,
        "role": user.role,
        "iat": int(datetime.datetime.utcnow().timestamp()),
        "exp": int((datetime.datetime.utcnow() + datetime.timedelta(hours=AUTH_EXP_HOURS)).timestamp()),
    }
    token = jwt.encode(payload, AUTH_SECRET, algorithm=AUTH_ALGO)
    return {"access_token": token, "token_type": "bearer"}


@app.get("/auth/verify")
def auth_verify(request: Request, token: str | None = None):
    # Permitir token por Authorization: Bearer <token> o query param ?token=
    if token is None:
        auth = request.headers.get("Authorization")
        if auth and auth.lower().startswith("bearer "):
            token = auth.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Missing token")
    try:
        decoded = jwt.decode(token, AUTH_SECRET, algorithms=[AUTH_ALGO])
        return {
            "ok": True,
            "sub": decoded.get("sub"),
            "uid": decoded.get("uid"),
            "role": decoded.get("role"),
            "exp": decoded.get("exp"),
        }
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


class RegisterRequest(BaseModel):
    username: str
    password: str
    role: str | None = "doctor"


@app.post("/auth/register")
def auth_register(req: RegisterRequest, db: Session = Depends(get_session), request: Request = None):
    # Control de registro: permitir si es el primer usuario o si se presenta un secreto
    existing = db.query(User).count()
    reg_secret_env = os.getenv("REGISTRATION_SECRET")
    has_secret = False
    if reg_secret_env:
        # Aceptar por header o query param
        h = request.headers.get("X-Registration-Secret") if request else None
        q = request.query_params.get("registration_secret") if request else None
        has_secret = (h == reg_secret_env) or (q == reg_secret_env)
    if existing > 0 and not has_secret:
        raise HTTPException(status_code=403, detail="Registration disabled")

    if db.query(User).filter(User.username == req.username).first():
        raise HTTPException(status_code=409, detail="Username already exists")

    hashed = pwd_hash.hash(req.password)
    u = User(username=req.username, password_hash=hashed, role=req.role or "doctor")
    db.add(u)
    db.commit()
    db.refresh(u)
    return {"id": u.id, "username": u.username, "role": u.role}


@app.get("/auth/me")
def auth_me(claims: dict = Depends(get_current_claims)):
    return {
        "sub": claims.get("sub"),
        "uid": claims.get("uid"),
        "role": claims.get("role"),
        "exp": claims.get("exp"),
    }

# --- Admin user management ---
class UserCreate(BaseModel):
    username: str
    password: str
    role: str = "doctor"

class UserPatch(BaseModel):
    password: str | None = None
    role: str | None = None

@app.get("/admin/users")
def admin_list_users(db: Session = Depends(get_session), claims: dict = Depends(require_roles("admin"))):
    rows = db.query(User).order_by(User.id.asc()).all()
    return [{"id": r.id, "username": r.username, "role": r.role, "created_at": r.created_at.isoformat()} for r in rows]

@app.post("/admin/users")
def admin_create_user(body: UserCreate, db: Session = Depends(get_session), claims: dict = Depends(require_roles("admin"))):
    if db.query(User).filter(User.username == body.username).first():
        raise HTTPException(status_code=409, detail="Username already exists")
    hashed = pwd_hash.hash(body.password)
    u = User(username=body.username, password_hash=hashed, role=body.role or "doctor")
    db.add(u)
    db.commit()
    db.refresh(u)
    return {"id": u.id, "username": u.username, "role": u.role}

@app.patch("/admin/users/{user_id}")
def admin_patch_user(user_id: int, body: UserPatch, db: Session = Depends(get_session), claims: dict = Depends(require_roles("admin"))):
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    if body.password:
        u.password_hash = pwd_hash.hash(body.password)
    if body.role:
        u.role = body.role
    db.add(u)
    db.commit()
    return {"id": u.id, "username": u.username, "role": u.role}

@app.delete("/admin/users/{user_id}")
def admin_delete_user(user_id: int, db: Session = Depends(get_session), claims: dict = Depends(require_roles("admin"))):
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(u)
    db.commit()
    return {"ok": True}

# Include Doctor module routes
try:
    from ecg_api.doctor_api import router as doctor_router
    app.include_router(doctor_router)
except Exception:
    # Router inclusion is best-effort to avoid breaking legacy flows if import fails
    pass