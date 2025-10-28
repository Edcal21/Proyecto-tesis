import numpy as np

def estimate_quality(signal_mV: np.ndarray, fs: float) -> dict:
	"""
	Estima calidad de señal con heurísticas:
	  - SNR aproximado: potencia total vs. potencia de alta frecuencia (>40Hz)
	  - Índice de artefactos: proporción de ventanas con std excesivo
	"""
	x = np.asarray(signal_mV, dtype=float)
	if x.size < int(fs * 2):
		return {"snr_db": float('nan'), "artifact_ratio": float('nan')}
	# Potencia total
	p_total = float(np.mean(x**2))
	# Filtro pasa alto simple vía diferencia (aprox HF)
	x_hf = x - np.convolve(x, np.ones(5)/5, mode='same')
	p_hf = float(np.mean(x_hf**2))
	snr = 10 * np.log10((p_total - p_hf) / (p_hf + 1e-12)) if p_hf > 0 else float('inf')

	# Artefactos por ventana: std grande
	win = int(fs * 2)
	n = x.size // win
	if n == 0:
		return {"snr_db": snr, "artifact_ratio": 0.0}
	count_art = 0
	for i in range(n):
		seg = x[i*win:(i+1)*win]
		if np.std(seg) > 3 * np.median(np.abs(x) + 1e-9):
			count_art += 1
	artifact_ratio = count_art / n
	return {"snr_db": float(snr), "artifact_ratio": float(artifact_ratio)}
