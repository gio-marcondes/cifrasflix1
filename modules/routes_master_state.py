import threading
import time
import uuid
from pathlib import Path

import numpy as np
from flask import jsonify, render_template, request, send_file
from werkzeug.utils import secure_filename

# Nota: Certifique-se de que a variável 'app' está declarada no arquivo principal 
# que importa este arquivo de rotas. Se usar Blueprints, altere os @app.route.

MASTER_ROOT = Path("static") / "masterizacao"
MASTER_UPLOADS = MASTER_ROOT / "uploads"
MASTER_PREVIEWS = MASTER_ROOT / "previews"
MASTER_ALLOWED_EXT = {".mp3", ".wav", ".flac", ".m4a", ".ogg", ".aac"}
MASTER_EQ_FREQS = np.array([31.0, 63.0, 125.0, 250.0, 500.0, 1000.0, 2000.0, 4000.0, 8000.0, 16000.0], dtype=np.float32)
MASTER_JOBS = {}
MASTER_LOCK = threading.Lock()
_MASTER_LIBROSA = None


def _master_librosa():
    global _MASTER_LIBROSA
    if _MASTER_LIBROSA is None:
        import librosa
        _MASTER_LIBROSA = librosa
    return _MASTER_LIBROSA
