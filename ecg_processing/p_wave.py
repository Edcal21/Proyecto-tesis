import numpy as np
from scipy.signal import find_peaks, butter, filtfilt

def detect_p_waves(ecg_signal, fs):
    """
    Detecta posibles ondas P en la señal ECG.
    Retorna los índices de los picos P.
    """
    b, a = butter(2, [0.5/(0.5*fs), 10/(0.5*fs)], btype='band')
    filtered = filtfilt(b, a, ecg_signal)
    peaks, _ = find_peaks(filtered, distance=int(0.2*fs), prominence=0.05)
    return peaks
