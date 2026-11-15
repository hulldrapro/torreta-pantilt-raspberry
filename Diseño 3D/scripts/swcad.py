import glob, math, pythoncom
import win32com.client as wc
from win32com.client import gencache
from win32com.client import VARIANT

M = 0.001

def connect():
    tl = pythoncom.LoadTypeLib(glob.glob(r"C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS\sldworks.tlb")[0])
    a = tl.GetLibAttr()
    mod = gencache.EnsureModule(str(a[0]), a[1], a[3], a[4])
    sw = mod.ISldWorks(wc.Dispatch("SldWorks.Application")._oleobj_)
    sw.Visible = True
    return mod, sw

class Part:
    PLANES = {"XY": "Alzado", "XZ": "Planta", "YZ": "Vista lateral"}

    def __init__(self, mod, sw):
        self.mod, self.sw = mod, sw
        tpl = sw.GetUserPreferenceStringValue(8)
        nd = sw.NewDocument(tpl, 0, 0, 0)
        self.doc = mod.IModelDoc2(nd._oleobj_)
        self.fm = self.doc.FeatureManager
        self.sm = self.doc.SketchManager
        self.n = 0

    def _plane(self, base, off):
        d = self.doc
        d.ClearSelection2(True)
        d.Extension.SelectByID2(self.PLANES[base], "PLANE", 0, 0, 0, False, 0, None, 0)
        if abs(off) < 1e-9:
            return
        # 8 = swRefPlaneReferenceConstraint_Distance ; 8+... flip with 2? use sign check
        flip = 0x100 if off < 0 else 0  # swRefPlaneReferenceConstraint_OptionFlip = 256
        p = self.fm.InsertRefPlane(8 | flip, abs(off) * M, 0, 0, 0, 0)
        if p is None:
            raise RuntimeError("plano")
        p = self.mod.IFeature(d.FeatureByPositionReverse(0)._oleobj_)
        nm = p.Name
        d.ClearSelection2(True)
        d.Extension.SelectByID2(nm, "PLANE", 0, 0, 0, False, 0, None, 0)
        d.BlankRefGeom()
        d.ClearSelection2(True)
        d.Extension.SelectByID2(nm, "PLANE", 0, 0, 0, False, 0, None, 0)

    def _sketch(self, base, off, shapes):
        self._plane(base, off)
        sm = self.sm
        sm.InsertSketch(True)
        sm.AddToDB = True
        for s in shapes:
            if s[0] == "c":
                _, x, y, r = s
                sm.CreateCircleByRadius(x * M, y * M, 0, r * M)
            else:
                pts = s[1] if s[0] == "p" else [(s[1], s[2]), (s[3], s[2]), (s[3], s[4]), (s[1], s[4])]
                for i in range(len(pts)):
                    a, b = pts[i], pts[(i + 1) % len(pts)]
                    sm.CreateLine(a[0] * M, a[1] * M, 0, b[0] * M, b[1] * M, 0)
        sm.AddToDB = False

    def vol(self):
        mp = self.doc.Extension.CreateMassProperty()
        try:
            return mp.Volume * 1e9
        except Exception:
            return 0.0

    def _extrude(self, cut, depth, rev):
        if cut:
            f = self.fm.FeatureCut4(True, False, not rev, 0, 0, depth * M, 0, False, False, False, False,
                                    0, 0, False, False, False, False, False, True, True, True, True, False, 0, 0, False, False)
        else:
            f = self.fm.FeatureExtrusion2(True, False, rev, 0, 0, depth * M, 0, False, False, False, False,
                                          0, 0, False, False, False, False, True, True, True, 0, 0, False)
        return f

    def op(self, base, a, b, shapes, cut=False):
        v0 = self.vol()
        self._sketch(base, a, shapes)
        f = self._extrude(cut, b - a, False)
        self.doc.ClearSelection2(True)
        v1 = self.vol()
        if f is None or (cut and v1 >= v0 - 1e-6) or (not cut and v1 <= v0 + 1e-6):
            raise RuntimeError(f"op fallo {base} {a}->{b} cut={cut} f={f is not None} dv={v1-v0:.1f}")
        return v1 - v0

    # coordenadas de modelo
    @staticmethod
    def _map(shapes, fn):
        out = []
        for s in shapes:
            if s[0] == "c":
                x, y = fn(s[1], s[2]); out.append(("c", x, y, s[3]))
            else:
                pts = s[1] if s[0] == "p" else [(s[1], s[2]), (s[3], s[2]), (s[3], s[4]), (s[1], s[4])]
                out.append(("p", [fn(u, v) for u, v in pts]))
        return out

    def z(self, a, b, shapes, cut=False):   # shapes en (X,Y)
        return self.op("XY", a, b, shapes, cut)

    def y(self, a, b, shapes, cut=False):   # shapes en (X,Z)
        return self.op("XZ", a, b, self._map(shapes, lambda u, v: (u, -v)), cut)

    def x(self, a, b, shapes, cut=False):   # shapes en (Y,Z)
        return self.op("YZ", a, b, self._map(shapes, lambda u, v: (-v, u)), cut)

    def box(self):
        part = self.mod.IPartDoc(self.doc._oleobj_)
        bs = part.GetBodies2(0, True) or []
        if not bs:
            return [0] * 6
        bx = [1e9, 1e9, 1e9, -1e9, -1e9, -1e9]
        for b in bs:
            v = self.mod.IBody2(b._oleobj_).GetBodyBox()
            for i in range(3):
                bx[i] = min(bx[i], v[i] * 1000); bx[i + 3] = max(bx[i + 3], v[i + 3] * 1000)
        return [round(x, 2) for x in bx]

    def nbodies(self):
        return len(self.mod.IPartDoc(self.doc._oleobj_).GetBodies2(0, True) or [])

    def save(self, sldprt, stl=None, jpg=None):
        d = self.doc
        d.SaveAs3(sldprt, 0, 1)
        if stl:
            d.SaveAs3(stl, 0, 1)
        if jpg:
            self.sw.ActivateDoc3(d.GetTitle(), False, 0, 0)
            d.ShowNamedView2("*Isométrica", 7)
            d.ViewZoomtofit2()
            d.SaveAs3(jpg, 0, 1)

    def close(self):
        self.sw.CloseDoc(self.doc.GetTitle())
