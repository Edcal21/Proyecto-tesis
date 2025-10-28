import streamlit as st
import websocket
import threading
import json
import os

st.title("ECG en tiempo real (WebSocket)")

data_points = st.session_state.get("data_points", [])

def on_message(ws, message):
    data = json.loads(message)
    data_points.append(data["voltage_mV"])
    st.session_state.data_points = data_points[-250:]  # Mantén los últimos 10s si fs=25Hz

def run_ws():
    ws_url = os.getenv("WS_URL", "ws://localhost:8000/ws/ecg")
    ws = websocket.WebSocketApp(ws_url, on_message=on_message)
    ws.run_forever()

if st.button("Iniciar stream"):
    threading.Thread(target=run_ws, daemon=True).start()

st.line_chart(st.session_state.get("data_points", []))