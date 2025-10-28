from __future__ import annotations

from typing import Any, Optional
import os
from huggingface_hub import hf_hub_download
import joblib


def load_ecg2hrv(repo_id: str = "hubii-world/ECG2HRV", filename: str = "ECG2HRV.joblib", token: str | None = None) -> Any:
    """
    Descarga y carga un modelo desde Hugging Face Hub.

    - repo_id: Repo en HF Hub.
    - filename: Nombre del artefacto dentro del repo.
    - token: Token opcional (si el repo es privado). Si None, usa HUGGINGFACE_HUB_TOKEN del entorno.

    Retorna el objeto cargado por joblib.load.
    """
    if token is None:
        token = os.getenv("HUGGINGFACE_HUB_TOKEN")
    path = hf_hub_download(repo_id=repo_id, filename=filename, token=token)
    model = joblib.load(path)
    return model


_MODEL_SINGLETON: Any | None = None


def get_ecg2hrv_model() -> Optional[Any]:
    global _MODEL_SINGLETON
    if _MODEL_SINGLETON is not None:
        return _MODEL_SINGLETON
    try:
        _MODEL_SINGLETON = load_ecg2hrv()
        return _MODEL_SINGLETON
    except Exception:
        return None


def run_ecg2hrv(model: Any, signal, fs: float | None = None) -> dict:
    """
    Ejecuta el modelo con varias estrategias comunes (predict/transform/call).
    Retorna un dict con 'ok', 'output' o 'error'.
    """
    import numpy as np
    try:
        x = np.asarray(signal, dtype=float)
        if x.ndim == 1:
            X = x.reshape(1, -1)
        else:
            X = x
        # 1) predict(X)
        if hasattr(model, 'predict'):
            out = model.predict(X)
            return {"ok": True, "output": out.tolist() if hasattr(out, 'tolist') else out}
        # 2) transform(X)
        if hasattr(model, 'transform'):
            out = model.transform(X)
            return {"ok": True, "output": out.tolist() if hasattr(out, 'tolist') else out}
        # 3) callable(model)(signal[, fs])
        if callable(model):
            try:
                out = model(x, fs) if fs is not None else model(x)
            except TypeError:
                out = model(x)
            return {"ok": True, "output": out.tolist() if hasattr(out, 'tolist') else out}
        return {"ok": False, "error": "Modelo no soporta interfaces conocidas"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
