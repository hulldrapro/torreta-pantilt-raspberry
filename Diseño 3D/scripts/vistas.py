"""Ensamble de prueba (Z del STEP -> arriba) y vistas de cada pieza sola, para ver cómo encajan."""
import os, sys
from swcad import *

ROOT = r"C:\Users\diazr\OneDrive\Escritorio\Trabajos Claude\IA Embebidos - Torreta Pan-Tilt\Diseño 3D"
SWD = os.path.join(ROOT, "SolidWorks")
TMP = sys.argv[1]
mod, sw = connect()
paths = [os.path.join(SWD, n + ".SLDPRT") for n in ("01_Base", "02_Fork", "03_Head")]
for p in paths:
    sw.OpenDoc6(p, 1, 1, "", 0, 0)
a = sw.NewDocument(sw.GetUserPreferenceStringValue(9), 0, 0, 0)
ad = mod.IModelDoc2(a._oleobj_); asm = mod.IAssemblyDoc(a._oleobj_)
mu = mod.IMathUtility(sw.GetMathUtility()._oleobj_)
comps = []
for p in paths:
    c = mod.IComponent2(asm.AddComponent5(p, 0, "", False, "", 0, 0, 0)._oleobj_)
    c.Transform2 = mu.CreateTransform(VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, [1, 0, 0, 0, 0, -1, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0]))
    comps.append(c)
ad.EditRebuild3()
sw.ActivateDoc3(ad.GetTitle(), False, 0, 0)
VIEWS = ("*Isométrica", "*Frontal", "*Derecha", "*Superior", "*Inferior", "*Posterior")


def shots(tag, views=VIEWS):
    for v in views:
        ad.ShowNamedView2(v, -1); ad.ViewZoomtofit2()
        ad.SaveAs3(os.path.join(TMP, f"{tag}_{v.strip('*')}.jpg"), 0, 1)


shots("asm", ("*Isométrica", "*Frontal", "*Derecha", "*Posterior"))
for i, c in enumerate(comps):
    for j, o in enumerate(comps):
        o.Visible = 1 if i == j else 0
    ad.GraphicsRedraw2()
    shots(c.Name2.split("-")[0])
for c in comps:
    c.Visible = 1
ad.SaveAs3(os.path.join(TMP, "prueba.SLDASM"), 0, 1)
