import React from 'react';

export default function Footer() {
  return (
    <footer style={{ background: 'transparent', padding: '28px 0' }}>
      <div className="landing-container" style={{ borderTop: '1px solid rgba(255,255,255,0.06)', paddingTop: 18 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12 }}>
          <div style={{ color: 'rgba(255,255,255,0.9)' }}>© {new Date().getFullYear()} Proyecto-tesis — Uso educativo, no diagnóstico.</div>
          <div style={{ color: 'rgba(255,255,255,0.85)' }}>Contacto: info@local.test</div>
        </div>
      </div>
    </footer>
  );
}
