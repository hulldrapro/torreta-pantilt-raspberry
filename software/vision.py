"""Visión de la torreta: cámara, localización de figuras con OpenCV y recorte para el clasificador.

OpenCV solo dice DÓNDE hay una figura (contornos). QUÉ figura es lo decide el modelo entrenado
(clasificador.py). El mismo recorte se usa al capturar el dataset y al clasificar en la torreta,
así el modelo ve en la presentación exactamente el mismo tipo de imagen con el que se entrenó.
"""
import time

import cv2
import numpy as np

ANCHO, ALTO = 640, 480
AREA_MIN = 1500          # px²: contornos más pequeños se ignoran (ruido)
AREA_MAX_FRAC = 0.6      # contornos más grandes que el 60 % de la imagen se ignoran (el borde de la hoja, sombras)
MARGEN = 0.18            # el recorte se amplía un 18 % por lado para que el modelo vea el borde completo


class Camara:
    """Pi Camera (picamera2) o webcam USB. Siempre entrega imágenes BGR de ANCHO x ALTO."""

    def __init__(self, usb=False, indice=0):
        self.usb = usb
        if usb:
            self.cam = cv2.VideoCapture(indice)
            self.cam.set(cv2.CAP_PROP_FRAME_WIDTH, ANCHO)
            self.cam.set(cv2.CAP_PROP_FRAME_HEIGHT, ALTO)
        else:
            from picamera2 import Picamera2
            self.cam = Picamera2()
            # En picamera2, "RGB888" deja los píxeles en orden B,G,R: justo lo que usa OpenCV.
            self.cam.configure(self.cam.create_preview_configuration(main={"size": (ANCHO, ALTO), "format": "RGB888"}))
            self.cam.start()
        time.sleep(1.0)  # deja que se ajuste la exposición

    def leer(self):
        if self.usb:
            ok, frame = self.cam.read()
            if not ok:
                return None
            if frame.shape[1] != ANCHO:
                frame = cv2.resize(frame, (ANCHO, ALTO))
            return frame
        return self.cam.capture_array()

    def cerrar(self):
        if self.usb:
            self.cam.release()
        else:
            self.cam.stop()


def localizar(frame):
    """Busca figuras oscuras sobre fondo claro. Devuelve una lista de dicts con 'centro', 'caja', 'area', 'contorno'."""
    gris = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gris = cv2.GaussianBlur(gris, (5, 5), 0)
    _, bin_ = cv2.threshold(gris, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    bin_ = cv2.morphologyEx(bin_, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    # RETR_TREE y no RETR_EXTERNAL: la hoja blanca sobre una mesa oscura queda como un "hueco" del fondo,
    # y las figuras quedan DENTRO de ese hueco. Se toman los contornos de profundidad par (bordes externos
    # de algo oscuro), no los de profundidad impar (huecos).
    contornos, jer = cv2.findContours(bin_, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    if jer is None:
        return []
    jer = jer[0]
    area_max = AREA_MAX_FRAC * frame.shape[0] * frame.shape[1]
    out = []
    for i, c in enumerate(contornos):
        prof, padre = 0, jer[i][3]
        while padre != -1:
            prof, padre = prof + 1, jer[padre][3]
        if prof % 2:
            continue
        area = cv2.contourArea(c)
        if area < AREA_MIN or area > area_max:
            continue
        x, y, w, h = cv2.boundingRect(c)
        # Figuras cortadas por el borde de la imagen se ignoran: el modelo no las vería completas.
        if x <= 2 or y <= 2 or x + w >= frame.shape[1] - 2 or y + h >= frame.shape[0] - 2:
            continue
        m = cv2.moments(c)
        out.append({"centro": (int(m["m10"] / m["m00"]), int(m["m01"] / m["m00"])),
                    "caja": (x, y, w, h), "area": area, "contorno": c})
    out.sort(key=lambda f: f["area"], reverse=True)
    return out


def recortar(frame, caja):
    """Recorte cuadrado alrededor de la figura (con margen). Devuelve BGR."""
    x, y, w, h = caja
    lado = int(max(w, h) * (1 + 2 * MARGEN))
    cx, cy = x + w // 2, y + h // 2
    x0, y0 = cx - lado // 2, cy - lado // 2
    # Si el cuadrado se sale de la imagen, se rellena con el color del fondo (blanco) en vez de deformar.
    pad = max(0, -x0, -y0, x0 + lado - frame.shape[1], y0 + lado - frame.shape[0])
    if pad:
        frame = cv2.copyMakeBorder(frame, pad, pad, pad, pad, cv2.BORDER_REPLICATE)
        x0, y0 = x0 + pad, y0 + pad
    return frame[y0:y0 + lado, x0:x0 + lado].copy()
