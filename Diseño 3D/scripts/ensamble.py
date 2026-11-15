"""Ensamble de la torreta pan-tilt (SG90 x2 + cámara Raspberry Pi) en SolidWorks 2024.
Las piezas del STEP vienen todas en el mismo marco (Z hacia arriba, base en z=0).
Medidas sacadas con cilindros.py:
  - Servo de giro (pan): eje en (0,0), orejas bajo la cara inferior del Fork (z=23.9), tornillos en x=-8.8 y 19.0.
  - Servo de inclinación (tilt): dentro del Head, eje sobre Y en (x=2.2, z=76.5), cuerno en el brazo del Fork (y=21).
  - Cara frontal del Head (x=-8.9): 4 agujeros M3 en y=±13.85, z=80.7 / 108.4 -> ahí va el adaptador de cámara.
Al final todo se gira para que Z del STEP quede hacia arriba (Y de SolidWorks).
"""
import os
from swcad import *

ROOT = r"C:\Users\diazr\OneDrive\Escritorio\Trabajos Claude\IA Embebidos - Torreta Pan-Tilt\Diseño 3D"
SWD = os.path.join(ROOT, "SolidWorks")
AUX = os.path.join(SWD, "Ensamble", "Piezas_no_impresas")
STL = os.path.join(ROOT, "STL_Impresion")
IMG = os.path.join(ROOT, "Imagenes")
for d in (AUX, STL, IMG):
    os.makedirs(d, exist_ok=True)
mod, sw = connect()
R = lambda y0, z0, y1, z1: ("r", min(y0, y1), min(z0, z1), max(y0, y1), max(z0, z1))
C = lambda u, v, r: ("c", u, v, r)

COLORES = {"pla": (0.15, 0.45, 0.85), "pla2": (0.95, 0.55, 0.10), "base": (0.2, 0.2, 0.2),
           "azul": (0.20, 0.30, 0.80), "pcb": (0.10, 0.45, 0.20), "negro": (0.1, 0.1, 0.1)}


def color(doc, nombre):
    r, g, b = COLORES[nombre]
    doc.MaterialPropertyValues = VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, [r, g, b, 0.5, 0.8, 0.3, 0.3, 0.0, 0.0])


def nueva(path, col, build, stl=None):
    p = Part(mod, sw)
    build(p)
    color(p.doc, col)
    p.save(path, stl=stl, jpg=os.path.join(IMG, os.path.basename(path).replace(".SLDPRT", ".jpg")) if stl else None)
    print(os.path.basename(path), p.box(), "vol", round(p.vol()), flush=True)
    p.close()
    return path


# ---------- piezas ----------
def servo(p):   # SG90: eje hacia -Z en el origen; orejas en z=0..2.5; cuerpo a lo largo de +Y
    p.z(-4.3, 18.4, [R(-6.1, -5.9, 6.1, 16.9)])
    p.z(0, 2.5, [R(-6.1, -10.6, 6.1, 21.6)])
    p.z(-1, 3.5, [C(0, -8.3, 1), C(0, 19.3, 1)], cut=True)
    p.z(-8.3, -4.3, [C(0, 0, 5.9)])
    p.z(-11.1, -8.3, [C(0, 0, 2.4)])
    p.z(-12.6, -11.1, [C(0, 0, 3.5)])
    p.z(-12.6, -11.1, [R(-2.5, 2, 2.5, 15)])


LENTE_Z = 97.0      # centro del lente (marco del STEP)
XC = -12.9          # cara delantera del adaptador


def adaptador(p):   # placa 36x36x4 en la cara frontal del Head (x = -12.9 .. -8.9)
    p.x(XC, -8.9, [R(-18, 76.5, 18, 112.5)])
    m3 = [C(y, z, 1.7) for y in (-13.85, 13.85) for z in (80.7, 108.4)]
    p.x(XC - 1, -7.9, m3, cut=True)
    p.x(XC - 1, XC + 2.5, [C(y, z, 3.1) for y in (-13.85, 13.85) for z in (80.7, 108.4)], cut=True)   # avellanado cabeza M3
    m2 = [C(y, z, 1.1) for y in (-10.5, 10.5) for z in (LENTE_Z, LENTE_Z - 12.5)]
    p.x(XC - 1, -7.9, m2, cut=True)


def camara(p):      # Raspberry Pi Camera Module v2/v3: placa 25 x 23.86 x 1, a 3 mm del adaptador
    zb = LENTE_Z - 14.5
    x1 = XC - 3.0
    p.x(x1 - 1.0, x1, [R(-12.5, zb, 12.5, zb + 23.86)])
    p.x(x1 - 2, x1 + 1, [C(y, z, 1.1) for y in (-10.5, 10.5) for z in (LENTE_Z, LENTE_Z - 12.5)], cut=True)
    p.x(x1 - 1.0 - 4.5, x1 - 1.0, [R(-4.25, LENTE_Z - 4.25, 4.25, LENTE_Z + 4.25)])   # lente
    p.x(x1, x1 + 2.5, [R(-8, zb, 8, zb + 5.5)])                                      # conector del cable plano


def separador(p):   # separadores M2 x 3 mm entre adaptador y cámara
    p.x(XC - 3.0, XC, [C(y, z, 2.0) for y in (-10.5, 10.5) for z in (LENTE_Z, LENTE_Z - 12.5)])
    p.x(XC - 4, XC + 1, [C(y, z, 1.1) for y in (-10.5, 10.5) for z in (LENTE_Z, LENTE_Z - 12.5)], cut=True)


# ---------- transformaciones (filas = imagen de los ejes X, Y, Z de la pieza) ----------
def mul(a, b):
    return [sum(a[3 * i + k] * b[3 * k + j] for k in range(3)) for i in range(3) for j in range(3)]


UP = [1, 0, 0, 0, 0, -1, 0, 1, 0]          # Z del STEP -> Y de SolidWorks (arriba)
I = [1, 0, 0, 0, 1, 0, 0, 0, 1]
PAN = [0, -1, 0, 1, 0, 0, 0, 0, 1]         # servo: Y->X, Z->Z (eje hacia abajo)
TILT = [1, 0, 0, 0, 0, 1, 0, -1, 0]        # servo: Y->Z, Z->-Y (eje hacia +Y, al brazo del Fork)


def cerrar_proyecto():   # cierra solo los documentos de este proyecto (para que no queden versiones viejas en memoria)
    for d in list(sw.GetDocuments() or []):
        d = mod.IModelDoc2(d._oleobj_)
        ruta = d.GetPathName() or ""
        if ruta.startswith(ROOT) or ruta.startswith(TMPDIR) or (not ruta and "Ensamblaje" in d.GetTitle()):
            sw.CloseDoc(d.GetTitle())


TMPDIR = os.environ.get("TEMP", "~~")


def main():
    cerrar_proyecto()
    P = lambda n: os.path.join(SWD, n + ".SLDPRT")
    s = nueva(os.path.join(AUX, "Servo_SG90.SLDPRT"), "azul", servo)
    cam = nueva(os.path.join(AUX, "Camara_RPi_v2.SLDPRT"), "pcb", camara)
    sep = nueva(os.path.join(AUX, "Separadores_M2x3.SLDPRT"), "negro", separador)
    ad = nueva(P("04_Adaptador_Camara"), "pla2", adaptador, stl=os.path.join(STL, "04_Adaptador_Camara.STL"))

    for n, c in (("01_Base", "base"), ("02_Fork", "pla"), ("03_Head", "pla2")):
        r = sw.OpenDoc6(P(n), 1, 1, "", 0, 0)
        doc = mod.IModelDoc2((r[0] if isinstance(r, tuple) else r)._oleobj_)
        color(doc, c)
        doc.Save3(1, 0, 0)
        doc.SaveAs3(os.path.join(STL, n + ".STL"), 0, 1)

    lista = [(P("01_Base"), I, (0, 0, 0)), (P("02_Fork"), I, (0, 0, 0)), (P("03_Head"), I, (0, 0, 0)),
             (ad, I, (0, 0, 0)), (cam, I, (0, 0, 0)), (sep, I, (0, 0, 0)),
             (s, PAN, (0, 0, 21.4)),            # orejas contra la cara inferior del Fork; cuerno en la Base (z 8.8..10.3)
             (s, TILT, (2.2, 10.3, 76.5))]       # orejas en el bolsillo del Head; cuerno en el brazo del Fork (y 21..22.5)

    for path in {l[0] for l in lista}:
        sw.OpenDoc6(path, 1, 1, "", 0, 0)
    a = sw.NewDocument(sw.GetUserPreferenceStringValue(9), 0, 0, 0)
    adoc = mod.IModelDoc2(a._oleobj_); asm = mod.IAssemblyDoc(a._oleobj_)
    mu = mod.IMathUtility(sw.GetMathUtility()._oleobj_)
    for path, rot, t in lista:
        c = mod.IComponent2(asm.AddComponent5(path, 0, "", False, "", 0, 0, 0)._oleobj_)
        rr = mul(rot, UP)
        tt = [sum(t[k] * UP[3 * k + j] for k in range(3)) * M for j in range(3)]
        c.Transform2 = mu.CreateTransform(VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, rr + tt + [1, 0, 0, 0]))
    adoc.EditRebuild3()
    adoc.ClearSelection2(True)
    for c in asm.GetComponents(True):
        mod.IComponent2(c._oleobj_).Select4(True, None, False)
    asm.FixComponent()
    adoc.ClearSelection2(True)
    adoc.ForceRebuild3(False)
    out = os.path.join(SWD, "Ensamble")
    adoc.SaveAs3(os.path.join(out, "Ensamble_Torreta_PanTilt.SLDASM"), 0, 1)
    for c in asm.GetComponents(True):
        c = mod.IComponent2(c._oleobj_)
        print(c.Name2, [round(x * 1000, 1) for x in c.GetBox(False, False)])
    sw.ActivateDoc3(adoc.GetTitle(), False, 0, 0)
    for vista, arch in (("*Isométrica", "Ensamble_isometrica.jpg"), ("*Frontal", "Ensamble_frontal.jpg"),
                        ("*Izquierda", "Ensamble_lateral.jpg"), ("*Dimétrica", "Ensamble_dimetrica.jpg")):
        adoc.ShowNamedView2(vista, -1); adoc.ViewZoomtofit2()
        adoc.SaveAs3(os.path.join(IMG, arch), 0, 1)
    try:
        im = asm.InterferenceDetectionManager
        im.TreatCoincidenceAsInterference = False
        res = im.GetInterferences() or []
        print("interferencias:", len(res))
        for r in res:
            r = mod.IInterference(r._oleobj_)
            bb = None
            try:
                bb = [round(v * 1000, 1) for v in mod.IBody2(r.GetInterferenceBody()._oleobj_).GetBodyBox()]
            except Exception as e:
                bb = str(e)[:60]
            print("  ", [mod.IComponent2(c._oleobj_).Name2 for c in r.Components], round(r.Volume * 1e9, 1), "mm3", bb)
        im.Done()
    except Exception as e:
        print("interferencias: error", e)


main()

