import React from 'react';
import { Link } from 'react-router-dom';
import Hero from './Hero';
import Header from './landing/Header';
import CTA from './landing/CTA';
import Footer from './landing/Footer';

export default function Home() {
  return (
    <div className="landing-page" style={{ minHeight: '100vh' }}>
      <Header />

      <main className="landing-main-center">
        <div className="landing-container">
          <div className="landing-hero-box">
            <div style={{ maxWidth: 780, width: '100%', textAlign: 'left', display: 'grid', gap: 16 }}>
              <Hero
                title="Monitoreo, análisis y alertas en tiempo real"
                subtitle="Conecta tu dispositivo de monitoreo."
                height={96}
              />
              <p className="lead hero-subtitle" style={{ marginTop: 8 }}>
                Captura señales con AD8232 + ADS1115, procesa en FastAPI y explora métricas en Streamlit. Inicio de sesión requerido.
              </p>
              <div className="landing-cta-row">
                <a href="https://github.com/Edcal21/Proyecto-tesis" target="_blank" rel="noreferrer" className="btn btn-ghost-light btn-lg">Ver en GitHub</a>
              </div>
            </div>
          </div>
        </div>
      </main>

      <CTA />
      <Footer />
    </div>
  );
}
