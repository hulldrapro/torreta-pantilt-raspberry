"""Importa los STEP de la torreta pan-tilt a SolidWorks, guarda .SLDPRT + imagen y muestra medidas."""
import os
from swcad import *

ROOT = r"C:\Users\diazr\OneDrive\Escritorio\Trabajos Claude\IA Embebidos - Torreta Pan-Tilt"
SRC = os.path.join(ROOT, "Diseño original")
OUT = os.path.join(ROOT, "Diseño 3D", "SolidWorks")
IMG = os.path.join(ROOT, "Diseño 3D", "Imagenes")
os.makedirs(OUT, exist_ok=True); os.makedirs(IMG, exist_ok=True)
mod, sw = connect()

for i, n in enumerate(["Base", "Fork", "Head"], 1):
    r = sw.LoadFile4(os.path.join(SRC, n + ".step"), "r", None, 0)
    doc = mod.IModelDoc2((r[0] if isinstance(r, tuple) else r)._oleobj_)
    p = Part.__new__(Part); p.mod, p.sw, p.doc = mod, sw, doc
    print(n, "caja mm:", p.box(), "vol mm3:", round(p.vol(), 1), "cuerpos:", p.nbodies(), flush=True)
    nombre = f"0{i}_{n}"
    p.save(os.path.join(OUT, nombre + ".SLDPRT"), jpg=os.path.join(IMG, nombre + ".jpg"))
    p.close()
