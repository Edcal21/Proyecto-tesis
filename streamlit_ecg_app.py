import streamlit as st
import pandas as pd
import numpy as np
import time
import matplotlib.pyplot as plt
from scipy.signal import find_peaks, butter, filtfilt
import wfdb
import os
import requests

API_BASE = os.getenv("API_BASE", "http://localhost:8000")
LOGIN_URL = os.getenv("LOGIN_URL", "http://localhost:3000/login")

st.set_page_config(page_title="ECG Stream", layout="wide")

## Título y tema

# --- Guardia de autenticación (JWT) ---
def _get_query_token():
    # Streamlit >= 1.30: st.query_params es la API soportada
    qp = st.query_params
    if isinstance(qp, dict):
        val = qp.get("token")
        # Si viniera como lista por compatibilidad, toma el primero
        if isinstance(val, list):
            return val[0] if val else None
        return val
    return None

def _verify_token(token: str) -> dict | None:
    try:
        r = requests.get(f"{API_BASE}/auth/verify", params={"token": token}, timeout=5)
        if r.status_code == 200:
            return r.json()
    except Exception:
        return None
    return None

# Actualizar sesión si llega un token nuevo por query
token_q = _get_query_token()
if token_q and token_q != st.session_state.get('auth_token'):
    info = _verify_token(token_q)
    if info:
        st.session_state.auth_user = info
        st.session_state.auth_token = token_q
    else:
        st.session_state.auth_user = None
        st.session_state.auth_token = None

# Si aún no hay sesión válida, intentar con token previo o exigir login
if 'auth_user' not in st.session_state or st.session_state.get('auth_user') is None:
    token = st.session_state.get('auth_token') or token_q
    info = _verify_token(token) if token else None
    if info:
        st.session_state.auth_user = info
        st.session_state.auth_token = token
    else:
        st.warning("Debes iniciar sesión para acceder al panel.")
        st.write("Serás redirigido al portal de login del médico.")
        st.link_button("Ir a login", LOGIN_URL)
        st.stop()

# Enforce doctor role
claims = st.session_state.get('auth_user')
if not claims or claims.get('role') != 'doctor':
    st.error("Acceso restringido: se requiere rol de doctor.")
    st.link_button("Ir a login", LOGIN_URL)
    st.stop()

# Toggle de tema (oscuro personalizado)
if 'theme_dark' not in st.session_state:
    st.session_state.theme_dark = True
st.sidebar.header("Apariencia")
st.session_state.theme_dark = st.sidebar.checkbox("Tema oscuro personalizado", value=st.session_state.theme_dark)

if st.session_state.theme_dark:
    # Estilos globales (tema) aplicados a toda la app
    st.markdown(
        """
        <style>
        html, body, [data-testid="stAppViewContainer"] {
            background-color: #3D5AA7 !important;
            color: #FFFFFF !important;
            font-family: 'Segoe UI', Arial, sans-serif;
        }
        [data-testid="stSidebar"], .st-emotion-cache-1d391kg, .st-emotion-cache-1v0mbdj {
            background-color: #445A99 !important;
        }
        .stButton>button {
            background-color: #7ABBE6 !important;
            color: #FFFFFF !important;
            border-radius: 8px;
            padding: 8px 24px;
            font-size: 16px;
            border: none;
            transition: background 0.2s;
            font-family: 'Segoe UI', Arial, sans-serif;
        }
        .stButton>button:hover {
            background-color: #5fa6d6 !important;
        }
        .stTextInput>div>input, .stSelectbox>div>div, .stNumberInput>div>div>input {
            border-radius: 6px;
            border: 1px solid #7ABBE6;
            background-color: #445A99 !important;
            color: #FFFFFF !important;
            font-family: 'Segoe UI', Arial, sans-serif;
        }
        h1, h2, h3, h4, h5 {
            color: #7ABBE6 !important;
            font-family: 'Segoe UI', Arial, sans-serif;
        }
        .stDataFrame, .stTable, [data-testid="stDataFrame"] {
            background-color: #445A99 !important;
            color: #FFFFFF !important;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        }
        .stMetric {
            background: rgba(0,0,0,0.1);
            padding: 8px 12px;
            border-radius: 8px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

# Animaciones y mejoras visuales (aplican siempre)
st.markdown(
    """
    <style>
    /* Hero + animaciones */
    .hero {
        background: linear-gradient(120deg, rgba(122,187,230,0.25), rgba(68,90,153,0.35));
        border-radius: 16px;
        padding: 14px 18px;
        display: flex;
        align-items: center;
        gap: 14px;
        margin: 8px 0 4px 0;
        box-shadow: 0 6px 18px rgba(0,0,0,0.12);
        border: 1px solid rgba(122,187,230,0.25);
    }
    .hero h2 { margin: 0 0 4px 0; }
    .hero p { margin: 0; opacity: 0.92; }
    .hero-heart { width: 36px; height: 36px; animation: heartbeat 1.3s ease-in-out infinite; }
    @keyframes heartbeat {
      0% { transform: scale(1); }
      25% { transform: scale(1.08); }
      40% { transform: scale(1); }
      60% { transform: scale(1.08); }
      100% { transform: scale(1); }
    }
    .fade-in { animation: fadeInUp 600ms ease both; }
    @keyframes fadeInUp { from { opacity: 0; transform: translate3d(0, 8px, 0);} to { opacity: 1; transform: translate3d(0, 0, 0);} }
    /* Hover sutil en tarjetas DataFrame */
    [data-testid="stDataFrame"]:hover { box-shadow: 0 8px 22px rgba(0,0,0,0.18); transition: box-shadow .2s ease; }
    /* Botones con micro-animación */
    .stButton>button { transform: translateZ(0); }
    .stButton>button:active { transform: scale(0.98); }
    </style>
    """,
    unsafe_allow_html=True,
)

# Marca (logo)
st.sidebar.header("Marca")
show_logo = st.sidebar.checkbox("Mostrar logo en cabecera", value=True)
logo_width = st.sidebar.number_input("Ancho logo (px)", min_value=32, max_value=512, value=120)
logo_file = st.sidebar.file_uploader("Sube tu logo (PNG/JPG)", type=["png","jpg","jpeg"])
logo_path = st.sidebar.text_input("o ruta local al logo", value="")

if logo_file is not None:
    st.session_state.logo_bytes = logo_file.read()
elif logo_path:
    try:
        with open(logo_path, "rb") as f:
            st.session_state.logo_bytes = f.read()
    except Exception:
        pass
elif 'logo_bytes' not in st.session_state:
    # Intentar logo por defecto
    for candidate in ["logo.png", "web_frontend/logo.png", "web_frontend/assets/logo.png"]:
        if os.path.exists(candidate):
            try:
                with open(candidate, "rb") as f:
                    st.session_state.logo_bytes = f.read()
            except Exception:
                pass
            break

# Animaciones (Lottie)
st.sidebar.header("Animaciones")
anim_enabled = st.sidebar.checkbox("Mostrar animación Lottie", value=True)
lottie_upload = st.sidebar.file_uploader(
    "Sube animación Lottie (JSON)",
    type=["json"],
    help="Opcional: si no subes, se intentará un archivo local o se usa el corazón animado por defecto"
)
if lottie_upload is not None:
    try:
        # Guardar en sesión para reutilizar
        st.session_state.lottie_json = __import__('json').load(lottie_upload)
    except Exception as e:
        st.warning(f"No se pudo cargar el JSON: {e}")

# Cabecera con logo + título + hero
title_text = "Estación de Monitoreo Cardíaco"
if show_logo and st.session_state.get("logo_bytes"):
    col_logo, col_title = st.columns([1,6])
    with col_logo:
        st.image(st.session_state.logo_bytes, width=logo_width)
    with col_title:
        st.title(title_text)
else:
    st.title(title_text)

from streamlit_lottie import st_lottie
import json
col_h1, col_h2 = st.columns([1,5])
with col_h1:
    lottie_data = st.session_state.get("lottie_json") if 'anim_enabled' in locals() and anim_enabled else None
    # Si no hay subida y está habilitado, intentar archivos locales por defecto
    if lottie_data is None and ('anim_enabled' in locals() and anim_enabled):
        for candidate in ["web_frontend/heart.json", "web_frontend/assets/heart.json"]:
            if os.path.exists(candidate):
                try:
                    with open(candidate, "r", encoding="utf-8") as f:
                        lottie_data = json.load(f)
                except Exception:
                    lottie_data = None
                break
    if ('anim_enabled' in locals() and anim_enabled) and lottie_data:
        st_lottie(lottie_data, height=90, loop=True)
    elif 'anim_enabled' in locals() and anim_enabled:
        st.markdown(
            """
            <div class=\"hero fade-in\" style=\"justify-content:center;\">\n                            <svg class=\"hero-heart\" viewBox=\"0 0 24 24\" fill=\"#FF6B6B\" xmlns=\"http://www.w3.org/2000/svg\" aria-hidden=\"true\">\n                                <path d=\"M12 21s-6.716-4.438-9.428-7.15C.86 12.138.5 10.91.5 9.75.5 7.126 2.626 5 5.25 5c1.52 0 2.944.664 3.9 1.72L12 9.8l2.85-3.08C15.806 5.664 17.23 5 18.75 5 21.374 5 23.5 7.126 23.5 9.75c0 1.16-.36 2.388-2.072 4.1C18.716 16.562 12 21 12 21z\"/>\n                            </svg>\n                        </div>
            """,
            unsafe_allow_html=True,
        )
with col_h2:
        st.markdown(
                """
                <div class="hero fade-in">
                    <div>
                        <h2>Monitoreo, análisis y alertas en tiempo real</h2>
                        <p>Conecta señales desde CSV, PhysioNet o sensor y detecta picos R, RR, HR y más.</p>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
        )

# --- Panel de notificaciones (sólo admin) ---
claims = st.session_state.get('auth_user')
if claims and claims.get('role') == 'admin':
    st.sidebar.header("Alertas y notificaciones")
    try:
        r = requests.get(f"{API_BASE}/admin/notifications", headers={"Authorization": f"Bearer {st.session_state.get('auth_token','')}"}, timeout=5)
        if r.status_code == 200:
            cfg = r.json()
        else:
            cfg = {"whatsapp_enabled": False, "whatsapp_to": None}
    except Exception:
        cfg = {"whatsapp_enabled": False, "whatsapp_to": None}

    wp_enabled = st.sidebar.checkbox("Enviar alertas por WhatsApp", value=bool(cfg.get('whatsapp_enabled')))
    wp_to = st.sidebar.text_input("Destino WhatsApp (whatsapp:+<código><número>)", value=cfg.get('whatsapp_to') or "")
    if st.sidebar.button("Guardar notificaciones"):
        try:
            body = {"whatsapp_enabled": wp_enabled, "whatsapp_to": wp_to.strip() or None}
            r = requests.post(
                f"{API_BASE}/admin/notifications",
                json=body,
                headers={"Authorization": f"Bearer {st.session_state.get('auth_token','')}"},
                timeout=8,
            )
            if r.status_code == 200:
                st.sidebar.success("Notificaciones actualizadas")
            else:
                st.sidebar.error(f"Error al guardar: {r.status_code} {r.text}")
        except Exception as e:
            st.sidebar.error(f"Error de red: {e}")

# Sidebar: data source
st.sidebar.header("Fuente de datos")
source = st.sidebar.radio(
    "Seleccionar fuente:",
    ("CSV file", "Local path", "SQLite DB (table)", "Simulated", "PhysioNet")
)


uploaded_file = None
file_path = None
db_path = None
full_df = None

if source == "CSV file":
    uploaded_file = st.sidebar.file_uploader("Sube un archivo CSV (formato timestamp_utc,raw,voltage_mV,filtered_mV,...)")
elif source == "Local path":
    file_path = st.sidebar.text_input("Ruta local al CSV", value="ecg_log.csv")
elif source == "SQLite DB (table)":
    db_path = st.sidebar.text_input("Ruta al archivo SQLite (.db)")
    table_name = st.sidebar.text_input("Nombre de la tabla (ej: ecg)", value="ecg")
elif source == "PhysioNet":
    record_input = st.sidebar.text_input("Registro PhysioNet (ej: 100)", value="")
    if st.sidebar.button("Cargar desde PhysioNet"):
        if not record_input.strip():
            st.sidebar.warning("Indica un número de registro (ej: 100)")
        else:
            try:
                sig, fields = wfdb.rdsamp(record_input, pn_dir='mitdb')
                fs_remote = fields.get('fs', 360)
                signal = sig[:, 0].astype(float)
                t = np.arange(len(signal)) / float(fs_remote)
                start = pd.Timestamp.utcnow()
                timestamps = [(start + pd.Timedelta(seconds=float(x))).isoformat() + 'Z' for x in t]
                df_remote = pd.DataFrame({'timestamp_utc': timestamps, 'voltage_mV': signal})
                # Cargar en memoria para visualización
                full_df = df_remote
                st.session_state.buffer = df_remote.copy()
                st.session_state.pointer = 0
                st.session_state.fs = fs_remote
                st.session_state.physionet_record = record_input
                st.success(f'Registro {record_input} cargado ({len(df_remote)} muestras, fs={fs_remote} Hz)')
            except Exception as e:
                st.error(f"Error leyendo registro WFDB: {e}")
elif source == "mHealth CSV":
    mhealth_path = st.sidebar.text_input("Ruta al archivo mHealth CSV", value="mhealth_raw_data.csv")
    nrows = st.sidebar.number_input("Filas a mostrar (para vista rápida)", min_value=100, max_value=100000, value=5000, step=1000)
    if st.sidebar.button("Cargar mHealth CSV"):
        try:
            # Lee solo las primeras nrows filas para no saturar memoria
            df_mh = pd.read_csv(mhealth_path, nrows=nrows)
            st.session_state.mhealth_df = df_mh
            st.success(f"Archivo {mhealth_path} cargado ({len(df_mh)} filas)")
        except Exception as e:
            st.error(f"Error leyendo mHealth CSV: {e}")
else:
    # simulated
    sim_freq = st.sidebar.number_input("Frecuencia de muestreo simulada (Hz)", min_value=50, max_value=2000, value=250)
    sim_hr = st.sidebar.number_input("Frecuencia cardíaca simulada (bpm)", min_value=30, max_value=180, value=70)

    # Mostrar info de PhysioNet si está cargado
    if 'physionet_record' in st.session_state and 'fs' in st.session_state:
        st.info(f"Registro PhysioNet cargado: {st.session_state['physionet_record']} (fs={st.session_state['fs']} Hz)")


# Si se cargó mHealth, permite elegir columna y graficar y usarla como señal principal
if source == "mHealth CSV" and 'mhealth_df' in st.session_state:
    df_mh = st.session_state.mhealth_df
    st.write("### Vista previa del archivo mHealth:")
    st.dataframe(df_mh.head(20))
    col = st.selectbox("Selecciona columna a usar como señal:", [c for c in df_mh.columns if c not in ("Activity", "subject")])
    st.line_chart(df_mh[col])
    # Adaptar el flujo principal para usar esta columna como señal
    # Simula el mismo flujo que para voltage_mV
    full_df = pd.DataFrame({
        'timestamp_utc': df_mh.index.astype(str),
        'voltage_mV': df_mh[col].values
    })
    st.session_state.buffer = full_df.copy()
    st.session_state.pointer = 0
    st.session_state.fs = st.sidebar.number_input("Frecuencia de muestreo (Hz) para mHealth", value=50.0)

st.sidebar.header("Visualización")
window_s = st.sidebar.number_input("Segundos a mostrar en la ventana", min_value=2, max_value=60, value=10)
update_interval = st.sidebar.number_input("Intervalo de actualización (s)", min_value=0.2, max_value=5.0, value=1.0, step=0.2)

# Detection parameters
st.sidebar.header("Detección R")
min_rr_ms = st.sidebar.number_input("RR mínimo (ms)", min_value=200, max_value=1000, value=250)
prominence = st.sidebar.number_input("Prominence para find_peaks (mV)", min_value=0.1, max_value=200.0, value=0.5)

# Controls
col1, col2, col3 = st.columns(3)
with col1:
    start = st.button("Start")
with col2:
    stop = st.button("Stop")
with col3:
    reset = st.button("Reset")

# Control de ejecución
if 'running' not in st.session_state:
    st.session_state.running = False
if start:
    st.session_state.running = True
if stop:
    st.session_state.running = False
if reset:
    st.session_state.pointer = 0
    if 'buffer' in st.session_state:
        st.session_state.buffer = pd.DataFrame()



# (PhysioNet ya está integrado en la selección de fuente)

# Estado y ayuda para PhysioNet
if source == "PhysioNet":
    if 'buffer' in st.session_state and isinstance(st.session_state.buffer, pd.DataFrame) and len(st.session_state.buffer) > 0:
        st.success(
            f"Registro {st.session_state.get('physionet_record','')} listo: "
            f"{len(st.session_state.buffer)} muestras, fs={st.session_state.get('fs','?')} Hz"
        )
        # Vista previa rápida (una sola vez por carga)
        if not st.session_state.get('physio_preview_shown', False):
            try:
                n_preview = min(2000, len(st.session_state.buffer))
                st.line_chart(st.session_state.buffer['voltage_mV'].iloc[:n_preview])
                st.session_state.physio_preview_shown = True
            except Exception:
                pass
    else:
        st.info("Ingresa un número de registro (ej: 100) y presiona 'Cargar desde PhysioNet' para cargar la señal.")

# Normalización de columnas para CSV/SQLite genérico
if source in ("CSV file", "Local path", "SQLite DB (table)") and full_df is not None:
    # Si no existe la columna de señal esperada, permitir elegir una
    if 'voltage_mV' not in full_df.columns:
        st.info("No se encontró la columna 'voltage_mV'. Selecciona qué columna usar como señal.")
        # Proponer solo columnas numéricas para señal
        numeric_cols = [c for c in full_df.columns if pd.api.types.is_numeric_dtype(full_df[c])]
        candidate_cols = numeric_cols if numeric_cols else list(full_df.columns)
        sel_signal = st.selectbox("Columna de señal", candidate_cols)
        if sel_signal:
            try:
                full_df['voltage_mV'] = pd.to_numeric(full_df[sel_signal], errors='coerce')
            except Exception:
                full_df['voltage_mV'] = full_df[sel_signal]
    # Ofrecer elegir timestamp si no existe
    if 'timestamp_utc' not in full_df.columns:
        ts_cols = [c for c in full_df.columns if c.lower().startswith('time') or 'date' in c.lower()]
        sel_ts = st.selectbox("Columna de tiempo (opcional)", ["(ninguna)"] + ts_cols)
        if sel_ts != "(ninguna)":
            try:
                full_df['timestamp_utc'] = pd.to_datetime(full_df[sel_ts], errors='coerce')
            except Exception:
                pass

# If simulated, generate on the fly
if source == "Simulated":
    fs_guess = sim_freq
else:
    # --- Definir estimate_fs antes de su uso ---
    def estimate_fs(df):
        if df is not None and 'timestamp_utc' in df.columns and len(df) > 2:
            t = pd.to_datetime(df['timestamp_utc'], errors='coerce')
            dt = t.diff().dt.total_seconds().dropna()
            if len(dt) > 0:
                return 1.0 / np.median(dt)
        return 250.0

    fs_guess = estimate_fs(full_df) if full_df is not None else None
    # Si cargamos desde PhysioNet, intenta usar fs de la sesión
    if 'fs' in st.session_state and (fs_guess is None):
        fs_guess = st.session_state.fs

fs = st.sidebar.number_input(
    "Frecuencia de muestreo (Hz) detectada/usar",
    value=float(fs_guess) if fs_guess else 250.0
)

import requests
API_BASE = os.getenv("API_BASE", "http://localhost:8000")

# --- Placeholders globales para métricas y gráficos ---
hr_text = st.empty()
rr_text = st.empty()
plot_placeholder = st.empty()

# --- Bucle principal de streaming y visualización ---
def main_stream_loop():
    global full_df, fs, sim_hr, window_s, update_interval, min_rr_ms, prominence, source
    if 'running' not in st.session_state:
        st.session_state.running = False
    if 'pointer' not in st.session_state:
        st.session_state.pointer = 0
    if 'buffer' not in st.session_state:
        st.session_state.buffer = pd.DataFrame()

    # Filtros para la señal
    def get_filter(fs):
        # Butterworth 4th order, 0.5-40 Hz
        nyq = 0.5 * fs
        low = 0.5 / nyq
        high = 40.0 / nyq
        b, a = butter(4, [low, high], btype='band')
        return b, a

    try:
        if not st.session_state.running:
            # Mostrar una ventana estática si hay datos (no hace loop infinito)
            if 'buffer' in st.session_state and len(st.session_state.buffer) > 0:
                buf = st.session_state.buffer.copy()
            elif full_df is not None:
                seg = full_df.iloc[:int(window_s*fs)]
                buf = seg.copy()
            else:
                buf = pd.DataFrame()
        else:
            # Simulación o adquisición en tiempo real
            if source == 'Simulated':
                n_samples = int(round(update_interval * fs))
                t0 = st.session_state.pointer / fs
                t = np.arange(n_samples) / fs + t0
                heart_rate = sim_hr
                f_hr = heart_rate / 60.0
                ecg_sim = 1.0 * np.sin(2*np.pi*f_hr*t) + 0.2*np.sin(2*np.pi*2*f_hr*t)
                ecg_sim += 0.05 * np.random.randn(len(t))
                times = pd.to_datetime((t*1e6).astype(int), unit='us')
                df_chunk = pd.DataFrame({'timestamp_utc': times, 'voltage_mV': ecg_sim*1000.0})
                st.session_state.pointer += n_samples
                if 'buffer' in st.session_state and len(st.session_state.buffer) > 0:
                    buf = pd.concat([st.session_state.buffer, df_chunk], ignore_index=True)
                else:
                    buf = df_chunk.copy()
                st.session_state.buffer = buf.copy()
            else:
                # Para fuentes reales, solo muestra la ventana actual
                if 'buffer' in st.session_state and len(st.session_state.buffer) > 0:
                    buf = st.session_state.buffer.copy()
                elif full_df is not None:
                    seg = full_df.iloc[:int(window_s*fs)]
                    buf = seg.copy()
                else:
                    buf = pd.DataFrame()

        if buf is None or len(buf) < 3:
            st.warning("No hay datos suficientes para mostrar.")
            return

        sig = buf['voltage_mV'].astype(float).values
        if 'timestamp_utc' in buf.columns:
            times = pd.to_datetime(buf['timestamp_utc'], errors='coerce')
            t0 = times.iloc[0]
            rel_t = (times - t0).dt.total_seconds().fillna(np.linspace(0, (len(sig)-1)/fs, len(sig))).values
        else:
            rel_t = np.arange(len(sig))/fs

        # Filtro
        b, a = get_filter(fs)
        try:
            sig_f = filtfilt(b, a, sig)
        except Exception:
            sig_f = sig

        # Detección de picos R
        distance = int(max(1, (min_rr_ms/1000.0) * fs))
        peaks, props = find_peaks(sig_f, distance=distance, prominence=prominence)
        peak_times = rel_t[peaks]
        rr_intervals = np.diff(peak_times)
        rr_ms = rr_intervals * 1000.0
        hr_inst = 60.0 / rr_intervals if len(rr_intervals)>0 else np.array([])

        # Métricas
        if len(hr_inst)>0:
            hr_mean = np.nanmean(hr_inst)
            hr_text.metric("Heart rate (mean)", f"{hr_mean:.1f} bpm")
        else:
            hr_text.write("Heart rate: -- bpm")
        if len(rr_ms)>0:
            rr_text.write("RR intervals (ms): " + ", ".join([f"{x:.0f}" for x in rr_ms[-5:]]))
        else:
            rr_text.write("RR intervals: --")

        # Gráfico
        fig, ax = plt.subplots(figsize=(10,3))
        if st.session_state.get('theme_dark', False):
            fig.patch.set_facecolor('#3D5AA7')
            ax.set_facecolor('#445A99')
            ax.spines['bottom'].set_color('white')
            ax.spines['top'].set_color('white')
            ax.spines['left'].set_color('white')
            ax.spines['right'].set_color('white')
            ax.tick_params(axis='x', colors='white')
            ax.tick_params(axis='y', colors='white')
            label_color = 'white'
        else:
            label_color = 'black'
        ax.plot(rel_t, sig, label='raw', alpha=0.5, color='#AED9FB' if st.session_state.get('theme_dark', False) else None)
        ax.plot(rel_t, sig_f, label='filtered', color='#7ABBE6' if st.session_state.get('theme_dark', False) else None)
        ax.scatter(peak_times, sig_f[peaks], color='#FFB3B3' if st.session_state.get('theme_dark', False) else 'red', label='R peaks')
        ax.set_xlabel('Time (s)', color=label_color)
        ax.set_ylabel('mV', color=label_color)
        leg = ax.legend(loc='upper right')
        if st.session_state.get('theme_dark', False):
            for text in leg.get_texts():
                text.set_color('white')
        ax.grid(True, color='white' if st.session_state.get('theme_dark', False) else None, alpha=0.2 if st.session_state.get('theme_dark', False) else 1.0)
        plot_placeholder.pyplot(fig)

        # Exponer buffer actual para análisis avanzado
        st.session_state.current_sig = sig.tolist()
        st.session_state.current_fs = float(fs)

        # Solo dormir cuando está corriendo
        if st.session_state.running:
            time.sleep(update_interval)
    except Exception as e:
        st.error(f"Error en el bucle principal: {e}")


# --- Ejecutar el bucle principal ---
main_stream_loop()

# --- Sección de análisis avanzado (beta) ---
st.markdown("---")
st.header("Análisis avanzado (beta)")
col_btn, col_info = st.columns([1,3])
with col_btn:
    do_analyze = st.button("Analizar ventana actual")

analysis_out = st.session_state.get('last_analysis')
token = st.session_state.get('auth_token')

if do_analyze:
    sig_list = st.session_state.get('current_sig')
    fs_val = st.session_state.get('current_fs')
    if not sig_list or not fs_val:
        st.warning("No hay señal disponible aún. Espera unos segundos y vuelve a intentar.")
    else:
        try:
            headers = {"Authorization": f"Bearer {token}"} if token else {}
            payload = {"signal": sig_list, "fs": fs_val, "persist": True}
            r = requests.post(f"{API_BASE}/analysis", json=payload, headers=headers, timeout=15)
            if r.status_code == 200:
                analysis_out = r.json()
                st.session_state.last_analysis = analysis_out
            else:
                st.error(f"Error del backend: {r.status_code} {r.text}")
        except Exception as e:
            st.error(f"Error solicitando análisis: {e}")

if analysis_out:
    with st.expander("Resumen de métricas", expanded=True):
        hrv = analysis_out.get('hrv', {})
        quality = analysis_out.get('quality', {})
        ml = analysis_out.get('ml', {})
        col1, col2, col3 = st.columns(3)
        with col1:
            t = hrv.get('time', {})
            st.metric("SDNN (ms)", f"{t.get('SDNN', float('nan')):.1f}")
            st.metric("RMSSD (ms)", f"{t.get('RMSSD', float('nan')):.1f}")
            st.metric("pNN50 (%)", f"{t.get('pNN50', float('nan')):.1f}")
        with col2:
            f = hrv.get('freq', {})
            st.metric("LF", f"{f.get('LF', float('nan')):.4f}")
            st.metric("HF", f"{f.get('HF', float('nan')):.4f}")
            st.metric("LF/HF", f"{f.get('LF_HF', float('nan')):.2f}")
        with col3:
            st.metric("SNR (dB)", f"{quality.get('snr_db', float('nan')):.1f}")
            st.metric("Artefactos", f"{quality.get('artifact_ratio', float('nan')):.2f}")
            if quality.get('snr_db', 99) < 5 or quality.get('artifact_ratio', 0) > 0.3:
                st.warning("Calidad de señal baja: revisa electrodos/ruido")

    col_p, col_t = st.columns(2)
    with col_p:
        st.subheader("Poincaré")
        pc = hrv.get('poincare', {})
        pts = pc.get('points', []) or []
        if len(pts) >= 2:
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            figp, axp = plt.subplots(figsize=(4,4))
            axp.scatter(xs, ys, s=12, alpha=0.7)
            axp.set_xlabel('RRn (ms)')
            axp.set_ylabel('RRn+1 (ms)')
            axp.grid(True, alpha=0.3)
            st.pyplot(figp)
        else:
            st.write("Insuficiente para Poincaré")
    with col_t:
        st.subheader("Tachogram")
        tach = hrv.get('tachogram', {})
        ts = tach.get('t_s', [])
        rr = tach.get('rr_ms', [])
        if len(ts) >= 2 and len(rr) >= 2:
            figt, axt = plt.subplots(figsize=(5,3))
            axt.plot(ts, rr, '-o', ms=3)
            axt.set_xlabel('Tiempo (s)')
            axt.set_ylabel('RR (ms)')
            axt.grid(True, alpha=0.3)
            st.pyplot(figt)
        else:
            st.write("Insuficiente para tachogram")

    st.subheader("Espectro (Welch)")
    freq = hrv.get('freq', {})
    spec = freq.get('spectrum', {})
    f = spec.get('f')
    pxx = spec.get('pxx')
    if f and pxx and len(f) == len(pxx) and len(f) > 8:
        figw, axw = plt.subplots(figsize=(6,3))
        axw.plot(f, pxx)
        # bandas
        axw.axvspan(0.04, 0.15, color='orange', alpha=0.15, label='LF')
        axw.axvspan(0.15, 0.40, color='green', alpha=0.12, label='HF')
        axw.set_xlim(0.0, 0.5)
        axw.set_xlabel('Hz')
        axw.set_ylabel('PSD')
        axw.legend()
        axw.grid(True, alpha=0.3)
        st.pyplot(figw)
    else:
        st.write("Espectro no disponible")

    st.subheader("Clasificador (demo)")
    top = (analysis_out.get('ml') or {}).get('top_label')
    scores = (analysis_out.get('ml') or {}).get('scores') or {}
    if scores:
        st.write(f"Diagnóstico sugerido: {top}")
        try:
            st.bar_chart({"score": scores})
        except Exception:
            st.json(scores)
    else:
        st.write("Sin puntuaciones")

    st.subheader("Modelo ECG2HRV (Hugging Face)")
    hf_model = analysis_out.get('hf_model') or {}
    if hf_model.get('ok') is True:
        out = hf_model.get('output')
        try:
            import numpy as np
            import pandas as pd
            if isinstance(out, list):
                # Si es una lista de listas, mostrar tabla; si es 1D, mostrar como serie
                if len(out) > 0 and isinstance(out[0], list):
                    st.dataframe(pd.DataFrame(out))
                else:
                    st.write(out)
            elif isinstance(out, dict):
                st.json(out)
            else:
                # Intento de convertir a lista si es numpy
                if hasattr(out, 'tolist'):
                    st.write(out.tolist())
                else:
                    st.write(out)
        except Exception:
            st.json(hf_model)
    else:
        st.write(hf_model.get('error', 'Modelo no disponible'))

    # Feedback
    analysis_id = analysis_out.get('analysis_id')
    if analysis_id:
        st.subheader("Feedback del médico")
        chosen = st.radio("Selecciona veredicto", options=["normal","afib","av_block","pvcs"], index=["normal","afib","av_block","pvcs"].index(top) if top in ["normal","afib","av_block","pvcs"] else 0, horizontal=True)
        notes = st.text_area("Notas (opcional)")
        if st.button("Enviar feedback"):
            try:
                headers = {"Authorization": f"Bearer {token}"} if token else {}
                body = {"label": chosen, "notes": {"text": notes}}
                r = requests.post(f"{API_BASE}/analysis/{analysis_id}/feedback", json=body, headers=headers, timeout=10)
                if r.status_code == 200:
                    st.success("Feedback registrado")
                else:
                    st.error(f"Error al enviar feedback: {r.status_code} {r.text}")
            except Exception as e:
                st.error(f"Error de red al enviar feedback: {e}")

# Historial de eventos/alertas
st.markdown("---")
st.header("Historial")
col_e, col_a = st.columns(2)
with col_e:
    st.subheader("Eventos RR/HR")
    if st.button("Actualizar eventos"):
        try:
            r = requests.get(f"{API_BASE}/events")
            if r.status_code == 200:
                try:
                    data = r.json()
                except Exception:
                    data = None
                if data:
                    # Admite lista de dicts o dict
                    if isinstance(data, dict):
                        st.json(data)
                    else:
                        st.dataframe(pd.DataFrame(data))
                else:
                    st.write("Sin eventos disponibles.")
            else:
                st.error(f"Error del backend: {r.text}")
        except Exception as e:
            st.error(f"Error consultando eventos: {e}")



# --- FIN de los estilos y configuración visual ---

# --- Mensaje final de estado ---
st.write("App terminada / en pausa")

# Footer con branding
st.markdown(
        """
        <div style="margin-top:18px; text-align:center; opacity:0.85; font-size:13px;">
            Hecho con ❤️ por <strong>MediPulsenic</strong>
        </div>
        """,
        unsafe_allow_html=True,
)
