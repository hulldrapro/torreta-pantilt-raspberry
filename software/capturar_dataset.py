"""Captura el dataset con la MISMA cámara y el MISMO recorte que usa la torreta (lo recomienda la rúbrica).

Uso (en la Raspberry, con la torreta armada):
    python3 capturar_dataset.py --clase triangulo --n 300 --ver
    python3 capturar_dataset.py --clase otro --n 300 --ver      # manos, objetos, hojas arrugadas: lo que NO es objetivo

Mientras captura, mueve la hoja: más cerca, más lejos, girada, inclinada, con otra luz y con las
otras variantes impresas de la misma figura. Barra espaciadora = pausa/sigue, q = salir.
Las imágenes quedan en dataset/<clase>/. Al final comprime la carpeta dataset y súbela a Google Drive.
"""
import argparse
import os
import time

import cv2

import vision

CLASES = ["triangulo", "cuadrado", "circulo", "estrella", "cruz", "otro"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--clase", required=True, choices=CLASES)
    ap.add_argument("--n", type=int, default=300, help="cuántas imágenes guardar")
    ap.add_argument("--intervalo", type=float, default=0.25, help="segundos entre fotos")
    ap.add_argument("--salida", default="dataset")
    ap.add_argument("--ver", action="store_true", help="mostrar la imagen (necesita escritorio o VNC)")
    ap.add_argument("--usb", action="store_true", help="usar webcam USB en vez de la Pi Camera")
    a = ap.parse_args()

    carpeta = os.path.join(a.salida, a.clase)
    os.makedirs(carpeta, exist_ok=True)
    ya = len(os.listdir(carpeta))
    print(f"Clase '{a.clase}': ya hay {ya} imágenes. Voy a guardar {a.n} más en {carpeta}/")

    cam = vision.Camara(usb=a.usb)
    guardadas, pausa, ultimo = 0, False, 0.0
    for s in (3, 2, 1):
        print(f"Empieza en {s}...")
        time.sleep(1)
    try:
        while guardadas < a.n:
            frame = cam.leer()
            if frame is None:
                continue
            figuras = vision.localizar(frame)
            if figuras and not pausa and time.time() - ultimo >= a.intervalo:
                rec = vision.recortar(frame, figuras[0]["caja"])
                nombre = f"{a.clase}_{time.strftime('%Y%m%d_%H%M%S')}_{ya + guardadas:04d}.jpg"
                cv2.imwrite(os.path.join(carpeta, nombre), rec, [cv2.IMWRITE_JPEG_QUALITY, 92])
                guardadas += 1
                ultimo = time.time()
                if guardadas % 25 == 0:
                    print(f"  {guardadas}/{a.n}")
            if a.ver:
                vista = frame.copy()
                for i, f in enumerate(figuras):
                    x, y, w, h = f["caja"]
                    cv2.rectangle(vista, (x, y), (x + w, y + h), (0, 0, 255) if i == 0 else (0, 200, 0), 2)
                estado = "PAUSA" if pausa else "capturando"
                cv2.putText(vista, f"{a.clase}: {guardadas}/{a.n} ({estado})", (10, 25),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
                cv2.imshow("Captura dataset", vista)
                k = cv2.waitKey(1) & 0xFF
                if k == ord(" "):
                    pausa = not pausa
                elif k == ord("q"):
                    break
    finally:
        cam.cerrar()
        cv2.destroyAllWindows()
    print(f"Listo: {guardadas} imágenes nuevas en {carpeta}/ (total {ya + guardadas}).")


if __name__ == "__main__":
    main()
