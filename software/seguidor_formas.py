"""Torreta pan-tilt que detecta formas y sigue la forma objetivo (Raspberry Pi + Pi Camera + PCA9685 + 2 SG90).

Instalación (Raspberry Pi OS de 64 bits):
    sudo apt install -y python3-picamera2 python3-opencv
    pip install adafruit-circuitpython-servokit --break-system-packages
    Activar I2C:  sudo raspi-config -> Interface Options -> I2C

Uso:
    python3 seguidor_formas.py --forma triangulo            # sigue triángulos
    python3 seguidor_formas.py --forma cuadrado --ver       # muestra la imagen con lo detectado
    python3 seguidor_formas.py --sin-servos --ver           # prueba solo la visión (sin PCA9685)

Formas: triangulo, cuadrado, rectangulo, pentagono, hexagono, circulo.
"""
import argparse
import time

import cv2
import numpy as np

CANAL_PAN, CANAL_TILT = 0, 1
ANCHO, ALTO = 640, 480
KP = 0.035          # grados por píxel de error (control proporcional)
ZONA_MUERTA = 15    # px: si el error es menor, no se mueve (evita temblor)
AREA_MIN = 1500     # px²: ignora contornos pequeños (ruido)


# ---------------- visión ----------------
def clasificar(contorno):
    """Devuelve el nombre de la forma según el número de vértices del polígono aproximado."""
    peri = cv2.arcLength(contorno, True)
    aprox = cv2.approxPolyDP(contorno, 0.03 * peri, True)
    v = len(aprox)
    if v == 3:
        return "triangulo"
    if v == 4:
        x, y, w, h = cv2.boundingRect(aprox)
        return "cuadrado" if 0.85 <= w / float(h) <= 1.15 else "rectangulo"
    if v == 5:
        return "pentagono"
    if v == 6:
        return "hexagono"
    area = cv2.contourArea(contorno)
    circularidad = 4 * np.pi * area / (peri * peri) if peri else 0
    return "circulo" if circularidad > 0.75 else "otra"


def detectar(frame):
    """Lista de (forma, centro, contorno) de las figuras oscuras sobre fondo claro (o al revés con Otsu)."""
    gris = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gris = cv2.GaussianBlur(gris, (5, 5), 0)
    _, bin_ = cv2.threshold(gris, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    bin_ = cv2.morphologyEx(bin_, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    contornos, _ = cv2.findContours(bin_, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    out = []
    for c in contornos:
        if cv2.contourArea(c) < AREA_MIN:
            continue
        m = cv2.moments(c)
        if m["m00"] == 0:
            continue
        out.append((clasificar(c), (int(m["m10"] / m["m00"]), int(m["m01"] / m["m00"])), c))
    return out


# ---------------- servos ----------------
class Torreta:
    def __init__(self, usar_servos=True):
        self.pan, self.tilt = 90.0, 90.0
        self.kit = None
        if usar_servos:
            from adafruit_servokit import ServoKit
            self.kit = ServoKit(channels=16)
            for ch in (CANAL_PAN, CANAL_TILT):
                self.kit.servo[ch].set_pulse_width_range(500, 2400)   # rango típico del SG90
        self.mover(0, 0)

    def mover(self, d_pan, d_tilt):
        self.pan = float(np.clip(self.pan + d_pan, 0, 180))
        self.tilt = float(np.clip(self.tilt + d_tilt, 30, 150))  # limita la inclinación para no chocar con el Fork
        if self.kit:
            self.kit.servo[CANAL_PAN].angle = self.pan
            self.kit.servo[CANAL_TILT].angle = self.tilt


# ---------------- programa principal ----------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--forma", default="triangulo")
    ap.add_argument("--ver", action="store_true", help="mostrar ventana con lo detectado")
    ap.add_argument("--sin-servos", action="store_true")
    ap.add_argument("--usb", action="store_true", help="usar webcam USB en vez de la Pi Camera")
    a = ap.parse_args()

    if a.usb:
        cam = cv2.VideoCapture(0)
        cam.set(cv2.CAP_PROP_FRAME_WIDTH, ANCHO); cam.set(cv2.CAP_PROP_FRAME_HEIGHT, ALTO)
        leer = lambda: cam.read()[1]
    else:
        from picamera2 import Picamera2
        cam = Picamera2()
        cam.configure(cam.create_preview_configuration(main={"size": (ANCHO, ALTO), "format": "RGB888"}))
        cam.start(); time.sleep(1)
        leer = cam.capture_array

    t = Torreta(not a.sin_servos)
    perdido = 0
    try:
        while True:
            frame = leer()
            if frame is None:
                continue
            formas = detectar(frame)
            objetivos = [f for f in formas if f[0] == a.forma]
            if objetivos:
                perdido = 0
                forma, (cx, cy), c = max(objetivos, key=lambda f: cv2.contourArea(f[2]))
                ex, ey = cx - ANCHO // 2, cy - ALTO // 2
                # Si la torreta se mueve al revés, cambia el signo de ex o de ey.
                t.mover(-KP * ex if abs(ex) > ZONA_MUERTA else 0, KP * ey if abs(ey) > ZONA_MUERTA else 0)
            else:
                perdido += 1
                if perdido > 60:            # ~2 s sin ver la forma: barrido lento buscando
                    t.mover(1.0 if (perdido // 180) % 2 == 0 else -1.0, 0)
            if a.ver:
                for forma, (x, y), c in formas:
                    col = (0, 0, 255) if forma == a.forma else (0, 255, 0)
                    cv2.drawContours(frame, [c], -1, col, 2)
                    cv2.putText(frame, forma, (x - 30, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, col, 2)
                cv2.drawMarker(frame, (ANCHO // 2, ALTO // 2), (255, 0, 0), cv2.MARKER_CROSS, 20, 2)
                cv2.putText(frame, f"pan {t.pan:.0f}  tilt {t.tilt:.0f}", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
                cv2.imshow("Torreta", frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
    finally:
        t.pan, t.tilt = 90.0, 90.0
        t.mover(0, 0)
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
