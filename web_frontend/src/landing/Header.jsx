import React, { useState, useRef, useEffect } from 'react';
import { Link } from 'react-router-dom';

export default function Header({ onAdminClick }) {
  const [open, setOpen] = useState(false);
  const navRef = useRef(null);
  const btnRef = useRef(null);

  useEffect(() => {
    function handleDocClick(e) {
      const target = e.target;
      if (!open) return;
      if (navRef.current && navRef.current.contains(target)) return;
      if (btnRef.current && btnRef.current.contains(target)) return;
      setOpen(false);
    }

    function handleKey(e) {
      if (e.key === 'Escape') setOpen(false);
    }

    document.addEventListener('mousedown', handleDocClick);
    document.addEventListener('touchstart', handleDocClick);
    document.addEventListener('keydown', handleKey);
    return () => {
      document.removeEventListener('mousedown', handleDocClick);
      document.removeEventListener('touchstart', handleDocClick);
      document.removeEventListener('keydown', handleKey);
    };
  }, [open]);

  return (
    <header className="landing-header landing-container" role="banner">
      <div className="d-flex align-items-center" style={{ gap: 10 }}>
        <img src="/medinic-logo.png" alt="MEDINIC" height={36} onError={(e)=>{ e.currentTarget.style.display='none'; }} />
        <strong style={{ color: 'var(--landing-foreground)' }}>Plataforma ECG</strong>
      </div>

      <div className="landing-nav-wrap">
        <button
          ref={btnRef}
          className="landing-menu-button"
          onClick={() => setOpen((v) => !v)}
          aria-expanded={open}
          aria-controls="landing-navigation"
          aria-label={open ? 'Cerrar menú' : 'Abrir menú'}
          type="button"
        >
          {/* simple hamburger icon */}
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden>
            <path d="M4 6h16M4 12h16M4 18h16" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>

        {/* overlay covers the screen and closes menu on click */}
        {open && <div className="landing-nav-overlay" aria-hidden onClick={() => setOpen(false)} />}

        <nav id="landing-navigation" ref={navRef} className={`landing-nav ${open ? 'open' : ''}`}>
          <Link to="/" className="landing-nav-link">Inicio</Link>
          <Link to="/login" className="landing-nav-link">Ingresar</Link>
          <a href="https://github.com/Edcal21/Proyecto-tesis" target="_blank" rel="noreferrer" className="landing-nav-link">GitHub</a>
        </nav>
      </div>
    </header>
  );
}
