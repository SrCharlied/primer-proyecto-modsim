"""Hace importable el paquete ``gasolinera`` al correr pytest desde la raiz.

Con este archivo funcionan tanto ``python -m pytest -q`` como ``pytest -q``.
El plan usa la primera forma; esta es una red de seguridad para que a nadie
le falle el import por la forma de invocar pytest.
"""

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))
