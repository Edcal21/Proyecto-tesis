import React, { useEffect, useState } from 'react';
import Lottie from 'lottie-react';

const titleStyle = {
  margin: 0,
  fontSize: 24,
  lineHeight: 1.2,
};

const subtitleStyle = {
  margin: '6px 0 0',
  opacity: 0.9,
};

const heroBoxStyle = {
  display: 'flex',
  alignItems: 'center',
  gap: 12,
  padding: '12px 16px',
  borderRadius: 16,
  border: '1px solid rgba(0,0,0,0.06)',
  boxShadow: '0 6px 18px rgba(0,0,0,0.08)',
  background: 'linear-gradient(120deg, rgba(122,187,230,0.20), rgba(68,90,153,0.18))',
};

export default function Hero({
  title = 'Monitoreo, análisis y alertas en tiempo real',
  subtitle = 'Conecta señales desde CSV, PhysioNet o sensor y detecta picos R, RR, HR y más.',
  height = 80,
}) {
  const [animData, setAnimData] = useState(null);
  const [tried, setTried] = useState(false);

  useEffect(() => {
    let url = import.meta.env.VITE_LOTTIE_URL || '/heart.json';
    // Intentar cargar Lottie una sola vez
    if (!tried) {
      setTried(true);
      fetch(url)
        .then(async (r) => {
          if (!r.ok) throw new Error('no lottie');
          const json = await r.json();
          setAnimData(json);
        })
        .catch(() => setAnimData(null));
    }
  }, [tried]);

  return (
    <div style={heroBoxStyle}>
      {/* Animación a la izquierda */}
      <div style={{ width: height + 10, height: height, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        {animData ? (
          <Lottie animationData={animData} loop style={{ height }} />
        ) : (
          <>
            <style>{`
              @keyframes heartbeat { 0%{ transform: scale(1);} 25%{ transform: scale(1.08);} 40%{ transform: scale(1);} 60%{ transform: scale(1.08);} 100%{ transform: scale(1);} }
            `}</style>
            <svg
              viewBox="0 0 24 24"
              width={height}
              height={height}
              style={{ fill: '#FF6B6B', animation: 'heartbeat 1.3s ease-in-out infinite' }}
              aria-hidden="true"
            >
              <path d="M12 21s-6.716-4.438-9.428-7.15C.86 12.138.5 10.91.5 9.75.5 7.126 2.626 5 5.25 5c1.52 0 2.944.664 3.9 1.72L12 9.8l2.85-3.08C15.806 5.664 17.23 5 18.75 5 21.374 5 23.5 7.126 23.5 9.75c0 1.16-.36 2.388-2.072 4.1C18.716 16.562 12 21 12 21z"/>
            </svg>
          </>
        )}
      </div>
      {/* Texto a la derecha (se oculta si no hay contenido) */}
      {(title || subtitle) && (
        <div style={{ flex: 1 }}>
          {title && <h3 style={titleStyle}>{title}</h3>}
          {subtitle && <p style={subtitleStyle}>{subtitle}</p>}
        </div>
      )}
    </div>
  );
}
