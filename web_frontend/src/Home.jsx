import React from 'react';
import { Link } from 'react-router-dom';
import Hero from './Hero';

export default function Home() {
  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      flexDirection: 'column',
      background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 40%, #0ea5e9 100%)',
      color: 'white'
    }}>
      <header className="container py-3 d-flex justify-content-between align-items-center">
        <div className="d-flex align-items-center gap-2">
          <img src="/medinic-logo.png" alt="MEDINIC" height={32} onError={(e)=>{ e.currentTarget.style.display='none'; }} />
          <strong>Plataforma ECG</strong>
        </div>
        <nav>
          <Link to="/login" className="btn btn-light btn-sm">Ingresar</Link>
        </nav>
      </header>

      <main className="container" style={{ flex: 1, display: 'grid', placeItems: 'center', padding: '24px 16px' }}>
        <div style={{ maxWidth: 780, width: '100%', textAlign: 'left', display: 'grid', gap: 16 }}>
          <Hero
            title="Monitoreo, análisis y alertas en tiempo real"
            subtitle="Conecta la Raspberry Pi, analiza ECG y visualiza resultados en Streamlit."
            height={96}
          />
          <p className="lead" style={{ opacity: 0.95, marginTop: 8 }}>
            Captura señales con AD8232 + ADS1115, procesa en FastAPI y explora métricas en Streamlit. Inicio de sesión requerido.
          </p>
          <div className="d-flex gap-2 mt-2">
            <Link to="/login" className="btn btn-primary btn-lg">Ingresar</Link>
            <a href="https://github.com/Edcal21/Proyecto-tesis" target="_blank" rel="noreferrer" className="btn btn-outline-light btn-lg">Ver en GitHub</a>
          </div>
        </div>
      </main>

      <footer className="container py-3" style={{ opacity: 0.8, fontSize: 14 }}>
        <span>© {new Date().getFullYear()} Proyecto-tesis — Uso educativo, no diagnóstico.</span>
      </footer>
    </div>
  );
}
