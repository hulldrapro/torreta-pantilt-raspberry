"""Cierra en SolidWorks los documentos de este proyecto (para poder comprimirlos). Con 'abrir' vuelve a abrir el ensamble."""
import os, sys
from swcad import *

ROOT = r"C:\Users\diazr\OneDrive\Escritorio\Trabajos Claude\IA Embebidos - Torreta Pan-Tilt"
mod, sw = connect()
if len(sys.argv) > 1 and sys.argv[1] == "abrir":
    sw.OpenDoc6(os.path.join(ROOT, "Diseño 3D", "SolidWorks", "Ensamble", "Ensamble_Torreta_PanTilt.SLDASM"), 2, 0, "", 0, 0)
    print("abierto")
else:
    for d in list(sw.GetDocuments() or []):
        d = mod.IModelDoc2(d._oleobj_)
        r = d.GetPathName() or ""
        if r.startswith(ROOT) or "prueba" in r or (not r and "Ensamblaje" in d.GetTitle()):
            sw.CloseDoc(d.GetTitle())
    print("cerrados")
