"""Lee un STL y lista las coordenadas distintas (X, Y, Z) de los vértices dentro de una caja, para medir huecos."""
import struct, sys


def leer(path):
    data = open(path, "rb").read()
    if data[:5] == b"solid" and b"facet" in data[:300]:
        vs = []
        for ln in data.decode(errors="ignore").splitlines():
            ln = ln.strip()
            if ln.startswith("vertex"):
                vs.append(tuple(float(t) for t in ln.split()[1:4]))
        return vs
    n = struct.unpack("<I", data[80:84])[0]
    vs = []
    for i in range(n):
        o = 84 + i * 50 + 12
        for k in range(3):
            vs.append(struct.unpack("<3f", data[o + 12 * k:o + 12 * k + 12]))
    return vs


path, x0, x1, y0, y1, z0, z1 = sys.argv[1], *map(float, sys.argv[2:8])
vs = [v for v in leer(path) if x0 <= v[0] <= x1 and y0 <= v[1] <= y1 and z0 <= v[2] <= z1]
for i, n in enumerate("XYZ"):
    vals = sorted({round(v[i], 1) for v in vs})
    print(n, len(vals), vals if len(vals) < 60 else vals[:30] + ["..."] + vals[-30:])
