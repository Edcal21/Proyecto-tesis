import numpy as np
from scipy.signal import welch

def _time_domain(rr_ms: np.ndarray) -> dict:
    rr_diff = np.diff(rr_ms)
    rmssd = np.sqrt(np.mean(rr_diff ** 2)) if rr_diff.size > 0 else float('nan')
    sdnn = float(np.std(rr_ms)) if rr_ms.size > 1 else float('nan')
    # pNN50: porcentaje de diferencias sucesivas > 50 ms
    nn50 = int(np.sum(np.abs(rr_diff) > 50)) if rr_diff.size > 0 else 0
    pnn50 = (nn50 / rr_diff.size * 100.0) if rr_diff.size > 0 else float('nan')
    return {"SDNN": sdnn, "RMSSD": float(rmssd), "pNN50": float(pnn50)}

def _freq_domain(rr_ms: np.ndarray, fs_rr: float = 4.0) -> dict:
    """
    Aproximación: re-muestrear RR a frecuencia fija (fs_rr) linealmente y aplicar Welch.
    Bandas típicas: LF 0.04-0.15 Hz, HF 0.15-0.40 Hz.
    """
    if rr_ms.size < 3:
        return {"LF": float('nan'), "HF": float('nan'), "LF_HF": float('nan')}
    # Construir serie temporal de tiempos acumulados y remuestrear
    t = np.cumsum(rr_ms) / 1000.0
    t = t - t[0]
    # señal de intervalo instantáneo (RR en segundos)
    x = rr_ms / 1000.0
    # Re-muestreo a grid uniforme
    t_uniform = np.arange(0, t[-1], 1.0/fs_rr)
    if t_uniform.size < 8:
        return {"LF": float('nan'), "HF": float('nan'), "LF_HF": float('nan')}
    x_uniform = np.interp(t_uniform, t, x)
    f, pxx = welch(x_uniform, fs=fs_rr, nperseg=min(256, x_uniform.size))
    # Integrar potencias por banda
    def band_power(fmin, fmax):
        m = (f >= fmin) & (f < fmax)
        return float(np.trapz(pxx[m], f[m])) if np.any(m) else 0.0
    lf = band_power(0.04, 0.15)
    hf = band_power(0.15, 0.40)
    lf_hf = (lf / hf) if hf > 0 else float('nan')
    return {"LF": lf, "HF": hf, "LF_HF": lf_hf, "spectrum": {"f": f.tolist(), "pxx": pxx.tolist()}}

def _poincare(rr_ms: np.ndarray) -> dict:
    if rr_ms.size < 2:
        return {"SD1": float('nan'), "SD2": float('nan'), "points": []}
    x1 = rr_ms[:-1]
    x2 = rr_ms[1:]
    diff = (x2 - x1) / np.sqrt(2)
    sumv = (x2 + x1) / np.sqrt(2)
    sd1 = float(np.std(diff))
    sd2 = float(np.std(sumv))
    return {"SD1": sd1, "SD2": sd2, "points": list(map(lambda a,b: [float(a), float(b)], x1, x2))}

def compute_hrv(rr_intervals_ms):
    """
    Calcula métricas extendidas de HRV: time-domain (SDNN, RMSSD, pNN50),
    freq-domain (LF, HF, LF/HF, espectro), y Poincaré (SD1, SD2, puntos).
    También retorna el tachogram (RR vs tiempo).
    """
    rr = np.array(rr_intervals_ms, dtype=float)
    if rr.size == 0:
        return {"time": {}, "freq": {}, "poincare": {}, "tachogram": {}}
    time_metrics = _time_domain(rr)
    freq_metrics = _freq_domain(rr)
    poincare = _poincare(rr)
    tachogram = {"t_s": (np.cumsum(rr)/1000.0).tolist(), "rr_ms": rr.tolist()}
    return {"time": time_metrics, "freq": freq_metrics, "poincare": poincare, "tachogram": tachogram}
