import { useEffect } from 'react';

const STREAMLIT_URL = import.meta.env.VITE_STREAMLIT_URL || 'http://localhost:8501';
const STREAMLIT_DOCTOR_URL = import.meta.env.VITE_STREAMLIT_DOCTOR_URL || '';

export default function RedirectToStreamlit() {
  useEffect(() => {
    const url = new URL(window.location.href);
    let token = url.searchParams.get('token') || localStorage.getItem('access_token');
    const target = url.searchParams.get('target'); // e.g., 'doctor'
    if (!token) {
      // nothing to do, go back to login
      window.location.replace('/login');
      return;
    }
    // choose destination
    let dest = STREAMLIT_URL;
    if (target === 'doctor') {
      if (STREAMLIT_DOCTOR_URL) dest = STREAMLIT_DOCTOR_URL;
      else if (STREAMLIT_URL.includes(':8501')) dest = STREAMLIT_URL.replace(':8501', ':8502');
    }
  const enc = encodeURIComponent(token);
  const next = `${dest}/?token=${enc}&access_token=${enc}&jwt=${enc}`;
    window.location.replace(next);
  }, []);
  return null;
}
