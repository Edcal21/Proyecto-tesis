import numpy as np
from scipy.signal import find_peaks, butter, filtfilt

def detect_t_waves(ecg_signal, fs):
    """
    Detecta posibles ondas T en la señal ECG.
    Retorna los índices de los picos T.
    """
    b, a = butter(2, [1/(0.5*fs), 7/(0.5*fs)], btype='band')
    filtered = filtfilt(b, a, ecg_signal)
    peaks, _ = find_peaks(filtered, distance=int(0.3*fs), prominence=0.05)
    return peaks
