from __future__ import annotations

from typing import Dict, Any
import numpy as np


class ECGClassifier:
	"""
	Simple placeholder classifier. In a real setup, load a trained model
	(e.g., sklearn/onnx/torch) in __init__ and run inference in predict.
	"""

	def __init__(self):
		self.labels = [
			"normal",
			"afib",
			"av_block",
			"pvcs",
		]

	def predict(self, signal: np.ndarray, fs: float) -> Dict[str, Any]:
		"""
		Parameters:
		  - signal: ECG signal in mV (1D numpy array)
		  - fs: sampling rate in Hz
		Returns:
		  - dict with per-class scores and top_label
		"""
		if signal.size == 0 or fs <= 0:
			return {"scores": {}, "top_label": None}
		# Dummy heuristic features
		var = float(np.var(signal))
		mean_abs = float(np.mean(np.abs(signal)))
		# Map features to mock scores
		scores = {
			"normal": max(0.0, 1.0 - var),
			"afib": min(1.0, var * 0.5),
			"av_block": min(1.0, mean_abs * 0.3),
			"pvcs": min(1.0, var * 0.2 + mean_abs * 0.1),
		}
		top_label = max(scores, key=scores.get)
		return {"scores": scores, "top_label": top_label}


_singleton: ECGClassifier | None = None


def get_classifier() -> ECGClassifier:
	global _singleton
	if _singleton is None:
		_singleton = ECGClassifier()
	return _singleton
