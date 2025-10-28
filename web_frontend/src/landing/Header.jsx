import React from 'react';
import { Link } from 'react-router-dom';

export default function Header({ onAdminClick }) {
  return (
    <header className="landing-header landing-container" role="banner">
      <div className="d-flex align-items-center" style={{ gap: 10 }}>
        <img src="/medinic-logo.png" alt="MEDINIC" height={36} onError={(e)=>{ e.currentTarget.style.display='none'; }} />
        <strong style={{ color: 'var(--landing-foreground)' }}>Plataforma ECG</strong>
      </div>
      <nav>
        <Link to="/login" className="btn btn-light btn-sm">Ingresar</Link>
      </nav>
    </header>
  );
}
