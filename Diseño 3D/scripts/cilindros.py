"""Lista las caras cilíndricas (agujeros, ejes) de cada pieza: centro, eje, radio y largo, en mm."""
import os
from swcad import *

SWD = r"C:\Users\diazr\OneDrive\Escritorio\Trabajos Claude\IA Embebidos - Torreta Pan-Tilt\Diseño 3D\SolidWorks"
mod, sw = connect()
for n in ("01_Base", "02_Fork", "03_Head"):
    r = sw.OpenDoc6(os.path.join(SWD, n + ".SLDPRT"), 1, 1, "", 0, 0)
    doc = mod.IModelDoc2((r[0] if isinstance(r, tuple) else r)._oleobj_)
    part = mod.IPartDoc(doc._oleobj_)
    print("==", n)
    vistos = set()
    for b in part.GetBodies2(0, True):
        for f in mod.IBody2(b._oleobj_).GetFaces():
            f = mod.IFace2(f._oleobj_)
            s = mod.ISurface(f.GetSurface()._oleobj_)
            if not s.IsCylinder():
                continue
            p = s.CylinderParams  # origen(3), eje(3), radio
            bx = f.GetBox()
            key = tuple(round(v * 1000, 1) for v in p[:3]) + (round(p[6] * 1000, 2),)
            if key in vistos:
                continue
            vistos.add(key)
            print("  R=%.2f  centro=(%.1f, %.1f, %.1f)  eje=(%.0f, %.0f, %.0f)  caja z=%.1f..%.1f" % (
                p[6] * 1000, p[0] * 1000, p[1] * 1000, p[2] * 1000, p[3], p[4], p[5], bx[2] * 1000, bx[5] * 1000))
    sw.CloseDoc(doc.GetTitle())
