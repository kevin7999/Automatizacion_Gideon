import sys
import os

# Wrapper de retrocompatibilidad
CARPETA_RAIZ = os.path.dirname(os.path.abspath(__file__))
if CARPETA_RAIZ not in sys.path:
    sys.path.insert(0, CARPETA_RAIZ)

from main import main

if __name__ == "__main__":
    main()
