import React from 'react';
import { Link } from 'react-router-dom';

export default function CTA() {
  return (
    <section className="landing-cta-section" style={{ padding: '40px 0' }}>
      <div className="landing-container">
        <div className="landing-hero-box" style={{ display: 'flex', gap: 18, alignItems: 'center' }}>
          <div style={{ flex: 1 }}>
            <h2 style={{ margin: 0, fontSize: 22, color: 'var(--landing-foreground)' }}>Listo para monitorear tu ECG?</h2>
            <p style={{ marginTop: 8, color: 'rgba(255,255,255,0.9)' }}>Conecta tu sensor, visualiza en tiempo real y recibe alertas automáticas.</p>
          </div>
          <div style={{ display: 'flex', gap: 10 }}>
            <Link to="/login" className="btn btn-primary">Ingresar</Link>
            <a href="https://github.com/Edcal21/Proyecto-tesis" target="_blank" rel="noreferrer" className="btn btn-ghost-light">Ver en GitHub</a>
          </div>
        </div>
      </div>
    </section>
  );
}
