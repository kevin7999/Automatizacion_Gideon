import sys
import os
import ctypes

# Fijar AppUserModelID para que Windows muestre el icono propio en la barra de tareas
try:
    myappid = 'simpletv.gideon.hub.3.4.2_test'
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except Exception:
    pass

# Si se ejecuta empaquetado (.exe de PyInstaller), fijar el directorio de trabajo al directorio del ejecutable
if getattr(sys, 'frozen', False):
    CARPETA_RAIZ = os.path.dirname(os.path.abspath(sys.executable))
    os.chdir(CARPETA_RAIZ)
else:
    CARPETA_RAIZ = os.path.dirname(os.path.abspath(__file__))

if CARPETA_RAIZ not in sys.path:
    sys.path.insert(0, CARPETA_RAIZ)

from ui.app import AppGideon

def main():
    """Punto de entrada principal de G.I.D.E.O.N. 3.4.2 TEST"""
    app = AppGideon()
    app.mainloop()

if __name__ == "__main__":
    main()

