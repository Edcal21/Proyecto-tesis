import React, { useState } from 'react';
import { motion } from 'framer-motion';
import 'animate.css';
import './login-title-anim.css';
import './login.css';

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';
const STREAMLIT_URL = import.meta.env.VITE_STREAMLIT_URL || 'http://localhost:8501';
const ADMIN_EMAIL = import.meta.env.VITE_ADMIN_EMAIL || 'emorie.aguirre@gmail.com';
const ADMIN_WHATSAPP = import.meta.env.VITE_ADMIN_WHATSAPP || '+505 83797821';

export default function Login() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [accessRequested, setAccessRequested] = useState(false);
  const [accessSending, setAccessSending] = useState(false);

  const onSubmit = async (e) => {
    e.preventDefault();
    setError('');
    if (!username || !password) {
      setError('Completa usuario y contraseña');
      return;
    }
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      });
      let errorMsg = '';
      if (!res.ok) {
        try {
          const errData = await res.json();
          errorMsg = errData.detail || JSON.stringify(errData);
        } catch {
          errorMsg = 'Credenciales incorrectas';
        }
        throw new Error(errorMsg);
      }
  const data = await res.json();
  const token = data?.access_token;
      if (!token) throw new Error('No se recibió token');
  try { localStorage.setItem('access_token', token); } catch {}
  // Redirigir vía ruta de frontend; por defecto al perfil de doctor
  window.location.href = `/redirect?target=doctor&token=${encodeURIComponent(token)}`;
    } catch (err) {
      setError(err.message || 'Error');
    }
    finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <motion.div
        className="login-card"
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: 'easeOut' }}
      >
        {/* Logo de marca (se sirve desde /public). Si no existe, se oculta automáticamente. */}
        <div className="login-brand">
          <img
            src="/medinic-logo.png"
            alt="MEDINIC"
            onError={(e) => { e.currentTarget.style.display = 'none'; }}
          />
        </div>
        <h2 className="login-title login-title-anim">Accede al monitoreo</h2>
        <form onSubmit={onSubmit}>
          <input
            className="login-input"
            placeholder="Usuario"
            value={username}
            onChange={e => setUsername(e.target.value)}
          />
          <div className="password-wrapper">
            <input
              className="login-input"
              type={showPassword ? 'text' : 'password'}
              placeholder="Contraseña"
              value={password}
              onChange={e => setPassword(e.target.value)}
            />
              <button
                type="button"
                className="password-toggle btn btn-sm btn-link text-white-75 px-1 py-0"
                onClick={() => setShowPassword(v => !v)}
                aria-label={showPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'}
                data-bs-toggle="button"
                aria-pressed={showPassword ? 'true' : 'false'}
              >
                {showPassword ? 'Ocultar' : 'Mostrar'}
              </button>
          </div>
          <motion.button
            className="btn btn-primary w-100"
            whileHover={{ scale: 1.01 }}
            whileTap={{ scale: 0.99 }}
            type="submit"
            disabled={loading}
            data-bs-toggle="button"
            aria-pressed={loading ? 'true' : 'false'}
          >
            {loading ? 'Accediendo…' : 'Entrar'}
          </motion.button>
          {/* Grupo de acciones secundarias estilo Bootstrap */}
          <div className="d-flex justify-content-between align-items-center mt-2">
            <div className="d-inline-flex gap-2">
              <button
                type="button"
                className={`btn btn-outline-light btn-sm ${accessRequested ? 'active' : ''}`}
                data-bs-toggle="button"
                aria-pressed={accessRequested ? 'true' : 'false'}
                onClick={async () => {
                  if (accessRequested || accessSending) return;
                  setAccessSending(true);
                  try {
                    await fetch(`${API_BASE}/support/request-access`, {
                      method: 'POST',
                      headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify({ username, user_agent: navigator.userAgent })
                    });
                    setAccessRequested(true);
                  } catch (_) {
                    setAccessRequested(true);
                  } finally {
                    setAccessSending(false);
                  }
                }}
                title="Solicitar acceso al administrador"
              >
                {accessSending ? 'Enviando…' : 'Registrarse'}
              </button>
              <a className="btn btn-link btn-sm text-white-75" href="#" onClick={(e)=>e.preventDefault()}>
                Ayuda
              </a>
            </div>
          </div>
          {accessRequested && (
            <div className="alert alert-success py-2 px-3 mt-2 mb-0" role="alert">
              Solicitud de acceso preparada. Puedes contactar al administrador ahora:
              <div className="d-flex gap-2 mt-2 flex-wrap">
                <a
                  href={`mailto:${ADMIN_EMAIL}?subject=${encodeURIComponent('Solicitud de acceso - Plataforma ECG')}&body=${encodeURIComponent('Hola,\n\nMe gustaría solicitar acceso a la plataforma ECG.\nUsuario sugerido: ' + (username || '(sin usuario)') + '\n\nGracias.')}`}
                  className="btn btn-sm btn-light"
                >
                  Enviar correo
                </a>
                <a
                  href={`https://wa.me/${ADMIN_WHATSAPP.replace(/[^\d]/g,'')}?text=${encodeURIComponent('Hola, solicito acceso a la plataforma ECG. Usuario sugerido: ' + (username || '(sin usuario)'))}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn btn-sm btn-success"
                >
                  WhatsApp
                </a>
              </div>
              <div className="small opacity-75 mt-1">Admin: {ADMIN_EMAIL} — {ADMIN_WHATSAPP}</div>
            </div>
          )}
        </form>
        <div className="login-links">
          <label style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
            <input type="checkbox" /> Recordarme
          </label>
          <a href="#">Olvidé mi contraseña</a>
        </div>
        {error && (
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            style={{ color: 'crimson', marginTop: 8 }}
          >
            {error}
          </motion.p>
        )}
      </motion.div>
    </div>
  );
}
