def compute_intervals(r_peaks, p_peaks, t_peaks, fs):
    """
    Calcula intervalos PR, QT, etc. a partir de los índices de picos.
    """
    intervals = []
    for r in r_peaks:
        prev_p = [p for p in p_peaks if p < r]
        if prev_p:
            pr = (r - prev_p[-1]) / fs * 1000  # ms
            intervals.append(pr)
    return intervals
