import React from 'react';
import { Link } from 'react-router-dom';

export default function CTA() {
  return (
    <section className="landing-cta-section" style={{ padding: '40px 0' }}>
      <div className="landing-container">
        <div className="landing-hero-box landing-cta-box">
          <div className="landing-cta-content">
            <h2 className="landing-cta-title">Listo para monitorear tu ECG?</h2>
            <p className="landing-cta-subtitle">Conecta tu sensor, visualiza en tiempo real y recibe alertas automáticas.</p>
          </div>
          <div className="landing-cta-actions">
            <Link to="/login" className="btn btn-primary">Ingresar</Link>
            <a href="https://github.com/Edcal21/Proyecto-tesis" target="_blank" rel="noreferrer" className="btn btn-ghost-light">Ver en GitHub</a>
          </div>
        </div>
      </div>
    </section>
  );
}
