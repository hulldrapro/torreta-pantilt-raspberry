"""Actuadores y entradas de la torreta.

Actuadores (la rúbrica pide mínimo 3, sin contar LEDs):
  1. Servo PAN      (SG90, PCA9685 canal 0): gira la torreta.
  2. Servo TILT     (SG90, PCA9685 canal 1): inclina la cabeza.
  3. Servo GATILLO  (SG90, PCA9685 canal 2): "dispara" (martillo/bandera en el costado del Head).
  4. Buzzer pasivo  (GPIO18, PWM): alarmas y tonos distintos por clase.
Complementos: LED RGB (GPIO5/6/13) y botón de inicio (GPIO17 a GND).

Con simulado=True nada toca el hardware: todo se imprime en la terminal (para probar en el PC).
"""
import threading
import time

import numpy as np

CANAL_PAN, CANAL_TILT, CANAL_GATILLO = 0, 1, 2
PIN_BOTON, PIN_BUZZER = 17, 18
PIN_R, PIN_G, PIN_B = 5, 6, 13

PAN_MIN, PAN_MAX = 10, 170
TILT_MIN, TILT_MAX = 50, 130     # limita la inclinación para no chocar con el Fork
GATILLO_REPOSO, GATILLO_DISPARO = 20, 80

COLORES = {"apagado": (0, 0, 0), "rojo": (1, 0, 0), "verde": (0, 1, 0), "azul": (0, 0, 1),
           "amarillo": (1, 0.6, 0), "naranja": (1, 0.25, 0), "morado": (0.6, 0, 1), "blanco": (1, 1, 1)}


class Servos:
    def __init__(self, simulado=False):
        self.sim = simulado
        self.pan, self.tilt = 90.0, 90.0
        if not simulado:
            from adafruit_servokit import ServoKit
            self.kit = ServoKit(channels=16)
            for ch in (CANAL_PAN, CANAL_TILT, CANAL_GATILLO):
                self.kit.servo[ch].set_pulse_width_range(500, 2400)   # rango típico del SG90
            self.kit.servo[CANAL_GATILLO].angle = GATILLO_REPOSO
        self._escribir()

    def _escribir(self):
        self.pan = float(np.clip(self.pan, PAN_MIN, PAN_MAX))
        self.tilt = float(np.clip(self.tilt, TILT_MIN, TILT_MAX))
        if not self.sim:
            self.kit.servo[CANAL_PAN].angle = self.pan
            self.kit.servo[CANAL_TILT].angle = self.tilt

    def mover(self, d_pan, d_tilt):
        """Paso pequeño (control de seguimiento)."""
        self.pan += d_pan
        self.tilt += d_tilt
        self._escribir()

    def ir_a(self, pan, tilt, grados_por_s=120.0):
        """Movimiento suave hasta (pan, tilt): evita picos de corriente y que la imagen salga movida."""
        pasos = int(max(abs(pan - self.pan), abs(tilt - self.tilt)) / 2) + 1
        p0, t0 = self.pan, self.tilt
        for i in range(1, pasos + 1):
            self.pan = p0 + (pan - p0) * i / pasos
            self.tilt = t0 + (tilt - t0) * i / pasos
            self._escribir()
            time.sleep(2.0 / grados_por_s)
        if self.sim:
            print(f"   [servos] pan={self.pan:.0f}  tilt={self.tilt:.0f}")

    def disparar(self, veces=1):
        for _ in range(veces):
            if self.sim:
                print("   [gatillo] ¡DISPARO!")
            else:
                self.kit.servo[CANAL_GATILLO].angle = GATILLO_DISPARO
                time.sleep(0.18)
                self.kit.servo[CANAL_GATILLO].angle = GATILLO_REPOSO
            time.sleep(0.25)

    def asentir(self, veces=2):
        """La cabeza dice 'sí' (aliado)."""
        t = self.tilt
        for _ in range(veces):
            self.ir_a(self.pan, t - 15, 200)
            self.ir_a(self.pan, t + 15, 200)
        self.ir_a(self.pan, t, 200)

    def negar(self, veces=2):
        """La cabeza dice 'no' (bloqueo de disparo)."""
        p = self.pan
        for _ in range(veces):
            self.ir_a(p - 15, self.tilt, 200)
            self.ir_a(p + 15, self.tilt, 200)
        self.ir_a(p, self.tilt, 200)

    def apagar(self):
        self.ir_a(90, 90)
        if not self.sim:
            self.kit.servo[CANAL_GATILLO].angle = GATILLO_REPOSO
            time.sleep(0.3)
            for ch in (CANAL_PAN, CANAL_TILT, CANAL_GATILLO):
                self.kit.servo[ch].angle = None      # quita el PWM: los servos dejan de zumbar


class Buzzer:
    def __init__(self, simulado=False):
        self.sim = simulado
        if not simulado:
            from gpiozero import PWMOutputDevice
            self.dev = PWMOutputDevice(PIN_BUZZER, frequency=1000, initial_value=0)

    def tono(self, hz, seg):
        if self.sim:
            print(f"   [buzzer] {hz} Hz x {seg:.2f} s")
            time.sleep(seg)
            return
        self.dev.frequency = hz
        self.dev.value = 0.5
        time.sleep(seg)
        self.dev.value = 0

    def secuencia(self, notas):
        for hz, seg, pausa in notas:
            self.tono(hz, seg)
            time.sleep(pausa)

    # Sonidos (cada clase tiene el suyo)
    def inicio(self):        self.secuencia([(880, 0.08, 0.04), (1320, 0.12, 0)])
    def alarma(self):        self.secuencia([(2000, 0.08, 0.04), (1500, 0.08, 0.04)] * 4)
    def dos_pitidos(self):   self.secuencia([(1400, 0.15, 0.1)] * 2)
    def subida(self):        self.secuencia([(f, 0.07, 0) for f in range(600, 1800, 150)])
    def aliado(self):        self.secuencia([(523, 0.12, 0.03), (659, 0.12, 0.03), (784, 0.25, 0)])
    def grave(self):         self.tono(300, 0.7)
    def fin(self):           self.secuencia([(1320, 0.08, 0.04), (880, 0.15, 0)])

    def apagar(self):
        if not self.sim:
            self.dev.close()


class Led:
    def __init__(self, simulado=False):
        self.sim = simulado
        if not simulado:
            from gpiozero import RGBLED
            self.dev = RGBLED(PIN_R, PIN_G, PIN_B)     # LED de cátodo común (con resistencias de 220 Ω)

    def color(self, nombre):
        if self.sim:
            print(f"   [LED] {nombre}")
        else:
            self.dev.off()                   # detiene un parpadeo anterior
            self.dev.color = COLORES[nombre]

    def parpadear(self, nombre, periodo=0.5):
        if self.sim:
            print(f"   [LED] {nombre} parpadeando")
        else:
            self.dev.blink(on_time=periodo / 2, off_time=periodo / 2, on_color=COLORES[nombre])

    def apagar(self):
        if not self.sim:
            self.dev.close()


class Boton:
    """Pulsación corta = iniciar ciclo. Mantener 3 s = apagar la torreta.
    En simulación: Enter en la terminal o la barra espaciadora en la ventana."""

    def __init__(self, simulado=False):
        self.sim = simulado
        self._pulsado = threading.Event()
        self.apagar_pedido = threading.Event()
        if simulado:
            threading.Thread(target=self._leer_teclado, daemon=True).start()
        else:
            from gpiozero import Button
            self.dev = Button(PIN_BOTON, pull_up=True, bounce_time=0.05, hold_time=3)
            self._mantenido = False
            self.dev.when_pressed = self._presionado
            self.dev.when_held = self._mantener
            self.dev.when_released = self._soltado

    def _presionado(self):
        self._mantenido = False

    def _mantener(self):
        self._mantenido = True
        self.apagar_pedido.set()

    def _soltado(self):
        if not self._mantenido:             # si se mantuvo 3 s, ya contó como "apagar"
            self._pulsado.set()

    def _leer_teclado(self):
        while True:
            try:
                linea = input()
            except EOFError:                # sin terminal (p. ej. corriendo como servicio): solo queda la ventana
                return
            if linea.strip().lower() in ("q", "salir"):
                self.apagar_pedido.set()
            else:
                self._pulsado.set()

    def simular_pulso(self):
        self._pulsado.set()

    def fue_pulsado(self):
        if self._pulsado.is_set():
            self._pulsado.clear()
            return True
        return False
