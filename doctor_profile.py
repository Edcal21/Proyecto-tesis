import os
import base64
import json
import requests
import streamlit as st


API_BASE = os.getenv("API_BASE", "http://localhost:8000")
LOGIN_URL = os.getenv("LOGIN_URL", "http://localhost:3000/login")

st.set_page_config(page_title="Perfil de Doctor", layout="wide")


def _get_query_token():
    # Usar API soportada
    qp = st.query_params
    token = None
    if isinstance(qp, dict):
        cand = qp.get('token') or qp.get('access_token') or qp.get('jwt')
        if isinstance(cand, list):
            token = cand[0] if cand else None
        else:
            token = cand
    return token


def _verify_token(token: str):
    try:
        r = requests.get(f"{API_BASE}/auth/verify", params={"token": token}, timeout=10)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


token_q = _get_query_token()
# Si llega un token nuevo por query, verificarlo y refrescar la sesión SIEMPRE
if token_q and token_q != st.session_state.get('access_token'):
    claims = _verify_token(token_q)
    if claims:
        st.session_state['auth_user'] = claims
        st.session_state['access_token'] = token_q
    else:
        # token inválido: limpiar sesión para forzar login
        st.session_state['auth_user'] = None
        st.session_state['access_token'] = None

# Si aún no hay usuario autenticado, intentar con token ya guardado
if 'auth_user' not in st.session_state or st.session_state.get('auth_user') is None:
    token = st.session_state.get('access_token') or token_q
    if token:
        claims = _verify_token(token)
        if claims:
            st.session_state['auth_user'] = claims
            st.session_state['access_token'] = token
        else:
            st.session_state['auth_user'] = None
            st.session_state['access_token'] = None

claims = st.session_state.get('auth_user')
if not claims or claims.get('role') != 'doctor':
    st.warning("Se requiere iniciar sesión como doctor.")
    st.markdown(f"[Ir al login]({LOGIN_URL})")
    st.stop()


def _auth_headers():
    return {"Authorization": f"Bearer {st.session_state.get('access_token')}"}


st.title("Perfil de Doctor")

# Sidebar: Dark mode + Navigation
if 'theme_dark' not in st.session_state:
    st.session_state['theme_dark'] = False
st.sidebar.header("Opciones")
st.session_state['theme_dark'] = st.sidebar.checkbox("Tema oscuro", value=st.session_state['theme_dark'])


@st.cache_data(ttl=30)
def fetch_profile():
    r = requests.get(f"{API_BASE}/doctor/me", headers=_auth_headers(), timeout=15)
    r.raise_for_status()
    return r.json()


@st.cache_data(ttl=30)
def fetch_patients():
    r = requests.get(f"{API_BASE}/doctor/patients", headers=_auth_headers(), timeout=15)
    r.raise_for_status()
    return r.json()


def save_profile(body: dict):
    r = requests.patch(f"{API_BASE}/doctor/me", headers=_auth_headers() | {"Content-Type": "application/json"}, data=json.dumps(body), timeout=20)
    if r.status_code != 200:
        st.error(f"Error al guardar perfil: {r.text}")
    fetch_profile.clear()


def create_patient(body: dict):
    r = requests.post(f"{API_BASE}/doctor/patients", headers=_auth_headers() | {"Content-Type": "application/json"}, data=json.dumps(body), timeout=20)
    if r.status_code != 200:
        st.error(f"Error al crear paciente: {r.text}")
    fetch_patients.clear()


def patch_patient(pid: int, body: dict):
    r = requests.patch(f"{API_BASE}/doctor/patients/{pid}", headers=_auth_headers() | {"Content-Type": "application/json"}, data=json.dumps(body), timeout=20)
    if r.status_code != 200:
        st.error(f"Error al actualizar paciente: {r.text}")
    fetch_patients.clear()


def delete_patient(pid: int):
    r = requests.delete(f"{API_BASE}/doctor/patients/{pid}", headers=_auth_headers(), timeout=20)
    if r.status_code != 200:
        st.error(f"Error al eliminar paciente: {r.text}")
    fetch_patients.clear()


def fetch_analyses(query: dict):
    r = requests.post(f"{API_BASE}/doctor/analyses", headers=_auth_headers() | {"Content-Type": "application/json"}, data=json.dumps(query), timeout=30)
    if r.status_code != 200:
        st.error(f"Error al cargar análisis: {r.text}")
        return []
    return r.json()


def post_feedback(analysis_id: int, label: str, notes: dict | None):
    r = requests.post(f"{API_BASE}/doctor/feedback/{analysis_id}", headers=_auth_headers() | {"Content-Type": "application/json"}, data=json.dumps({"label": label, "notes": notes or {}}), timeout=20)
    if r.status_code != 200:
        st.error(f"Error al enviar feedback: {r.text}")


def export_pdf(analysis_id: int):
    r = requests.get(f"{API_BASE}/doctor/analysis/{analysis_id}/export-pdf", headers=_auth_headers(), timeout=60)
    if r.status_code == 200:
        return r.content
    else:
        st.error(f"Error al exportar PDF: {r.text}")
        return None


def get_alert_settings():
    r = requests.get(f"{API_BASE}/doctor/settings/alerts", headers=_auth_headers(), timeout=15)
    if r.status_code == 200:
        return r.json()
    return {}


def set_alert_settings(body: dict):
    r = requests.post(f"{API_BASE}/doctor/settings/alerts", headers=_auth_headers() | {"Content-Type": "application/json"}, data=json.dumps(body), timeout=20)
    if r.status_code != 200:
        st.error(f"Error al guardar ajustes: {r.text}")


def test_whatsapp():
    r = requests.post(f"{API_BASE}/doctor/notifications/test", headers=_auth_headers(), timeout=20)
    if r.status_code == 200:
        st.success(r.json())
    else:
        st.error(r.text)


def link_analysis(patient_id: int, analysis_id: int):
    r = requests.post(f"{API_BASE}/doctor/link-analysis", headers=_auth_headers() | {"Content-Type": "application/json"}, data=json.dumps({"patient_id": patient_id, "analysis_id": analysis_id}), timeout=20)
    if r.status_code != 200:
        st.error(f"Error al vincular análisis: {r.text}")


# --- Profile Form ---
prof = fetch_profile()
with st.expander("Datos del perfil", expanded=True):
    col1, col2 = st.columns([2,1])
    with col1:
        name = st.text_input("Nombre completo", prof.get("name", ""))
        email = st.text_input("Email profesional", prof.get("email", ""))
        specialty = st.selectbox("Especialidad", ["Cardiología", "Medicina Interna", "Otros"], index=["Cardiología","Medicina Interna","Otros"].index(prof.get("specialty") or "Cardiología"))
        license_number = st.text_input("Número de licencia", prof.get("license_number") or "")
        organization = st.text_input("Institución", prof.get("organization") or "")
        if st.button("Guardar perfil"):
            save_profile({
                "name": name,
                "email": email,
                "specialty": specialty,
                "license_number": license_number,
                "organization": organization,
                "profile_image_b64": prof.get("profile_image_b64"),
            })
    with col2:
        st.write("Foto de perfil")
        current_img_b64 = prof.get("profile_image_b64")
        if current_img_b64:
            st.image(base64.b64decode(current_img_b64), caption="Actual", use_container_width=True)
        up = st.file_uploader("Subir imagen", type=["png","jpg","jpeg"])
        if up is not None:
            data_b64 = base64.b64encode(up.read()).decode("utf-8")
            save_profile({
                "name": name,
                "email": email,
                "specialty": specialty,
                "license_number": license_number,
                "organization": organization,
                "profile_image_b64": data_b64,
            })
            st.experimental_rerun()


# --- Patients CRUD ---
st.subheader("Pacientes asignados")
patients = fetch_patients()
if patients:
    st.table(patients)
else:
    st.info("No hay pacientes registrados.")

with st.expander("Agregar/editar paciente"):
    pid = st.selectbox("Seleccionar paciente (para editar)", ["Nuevo"] + [f"{p['id']} - {p['name']}" for p in patients])
    name_p = st.text_input("Nombre", value="")
    email_p = st.text_input("Email", value="")
    ident_p = st.text_input("Identificador", value="")
    dob_p = st.text_input("Fecha de nacimiento (YYYY-MM-DD)", value="")
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("Crear paciente"):
            create_patient({"name": name_p, "email": email_p, "identifier": ident_p, "dob": dob_p})
    with c2:
        if st.button("Actualizar seleccionado") and pid != "Nuevo":
            pid_int = int(pid.split(" - ")[0])
            patch_patient(pid_int, {"name": name_p, "email": email_p, "identifier": ident_p, "dob": dob_p})
    with c3:
        if st.button("Eliminar seleccionado") and pid != "Nuevo":
            pid_int = int(pid.split(" - ")[0])
            delete_patient(pid_int)
            st.experimental_rerun()


# --- Analyses and Filters ---
st.subheader("Análisis HRV de pacientes")
sel_patient = st.selectbox("Paciente", ["Todos"] + [f"{p['id']} - {p['name']}" for p in patients])
abnormal = st.checkbox("Mostrar solo anormales (SDNN < 50 ms)", value=False)
metric = st.selectbox("Métrica", ["SDNN","RMSSD","pNN50"]) 
op = "lt" if st.radio("Condición", ["<", ">"], index=0) == "<" else "gt"
threshold = st.number_input("Umbral", value=50.0)

query = {
    "patient_id": None if sel_patient == "Todos" else int(sel_patient.split(" - ")[0]),
    "abnormal": abnormal,
    "metric": metric,
    "op": op,
    "threshold": threshold,
    "limit": 300,
}

rows = fetch_analyses(query)
if rows:
    st.dataframe(rows, use_container_width=True)
    # Actions on selected analysis
    ids = [r["analysis_id"] for r in rows]
    if ids:
        sel = st.selectbox("Elegir análisis", ids)
        colA, colB = st.columns(2)
        with colA:
            label = st.text_input("Diagnóstico")
            notes = st.text_area("Notas (JSON opcional)")
            if st.button("Enviar feedback"):
                try:
                    notes_obj = json.loads(notes) if notes.strip() else {}
                except Exception:
                    notes_obj = {"text": notes}
                post_feedback(sel, label, notes_obj)
        with colB:
            if st.button("Exportar PDF"):
                pdf = export_pdf(sel)
                if pdf:
                    st.download_button("Descargar PDF", data=pdf, file_name=f"hrv_report_{sel}.pdf", mime="application/pdf")
else:
    st.info("No hay análisis para mostrar.")


with st.expander("Ajustes de alertas (WhatsApp/Email)", expanded=False):
    s = get_alert_settings() or {}
    w_enabled = st.checkbox("WhatsApp habilitado", value=bool(s.get("whatsapp_enabled")))
    w_to = st.text_input("Destino WhatsApp (ej. whatsapp:+521...)", value=s.get("whatsapp_to") or "")
    e_enabled = st.checkbox("Email habilitado", value=bool(s.get("email_enabled")))
    e_to = st.text_input("Destino Email", value=s.get("email_to") or "")
    st.markdown("Umbrales clínicos (JSON)")
    thresholds_text = st.text_area("{\n  \"SDNN\": 50,\n  \"RMSSD\": 20\n}", value=json.dumps(s.get("thresholds", {"SDNN": 50, "RMSSD": 20}), indent=2))
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Guardar ajustes"):
            try:
                thr = json.loads(thresholds_text) if thresholds_text.strip() else {}
            except Exception:
                thr = {"SDNN": 50, "RMSSD": 20}
            set_alert_settings({
                "whatsapp_enabled": w_enabled,
                "whatsapp_to": w_to.strip() or None,
                "email_enabled": e_enabled,
                "email_to": e_to.strip() or None,
                "thresholds": thr,
            })
    with c2:
        if st.button("Enviar prueba WhatsApp"):
            test_whatsapp()


with st.expander("Vincular análisis existente a paciente", expanded=False):
    if patients:
        pid_sel = st.selectbox("Paciente", [f"{p['id']} - {p['name']}" for p in patients])
        aid = st.number_input("ID de análisis", min_value=1, step=1)
        if st.button("Vincular"):
            link_analysis(int(pid_sel.split(" - ")[0]), int(aid))
    else:
        st.info("Primero crea pacientes para vincular análisis.")
