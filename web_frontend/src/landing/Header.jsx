import React, { useState } from 'react';
import { Link } from 'react-router-dom';

export default function Header({ onAdminClick }) {
  const [open, setOpen] = useState(false);

  return (
    <header className="landing-header landing-container" role="banner">
      <div className="d-flex align-items-center" style={{ gap: 10 }}>
        <img src="/medinic-logo.png" alt="MEDINIC" height={36} onError={(e)=>{ e.currentTarget.style.display='none'; }} />
        <strong style={{ color: 'var(--landing-foreground)' }}>Plataforma ECG</strong>
      </div>

      <div className="landing-nav-wrap">
        <button
          className="landing-menu-button"
          onClick={() => setOpen((v) => !v)}
          aria-expanded={open}
          aria-label="Abrir menú"
          type="button"
        >
          {/* simple hamburger icon */}
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden>
            <path d="M4 6h16M4 12h16M4 18h16" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>

        <nav className={`landing-nav ${open ? 'open' : ''}`} onClick={() => setOpen(false)}>
          <Link to="/" className="landing-nav-link">Inicio</Link>
          <Link to="/login" className="landing-nav-link">Ingresar</Link>
          <a href="https://github.com/Edcal21/Proyecto-tesis" target="_blank" rel="noreferrer" className="landing-nav-link">GitHub</a>
        </nav>
      </div>
    </header>
  );
}
