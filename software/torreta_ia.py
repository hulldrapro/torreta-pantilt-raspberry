"""Torreta CIWS con IA: identifica figuras con un modelo MobileNetV2 (TFLite) y reacciona según la clase.

Ciclo completo con un solo botón:
  1. ESPERA      LED azul parpadeando. Se oprime el botón.
  2. BARRIDO     La torreta gira de lado a lado; OpenCV localiza figuras y el modelo las clasifica.
  3. PRIORIDAD   Ordena lo encontrado por nivel de amenaza (identificación amigo-enemigo).
  4. ENFRENTAR   Para cada objetivo: apunta, lo sigue hasta centrarlo, confirma la clase por votación
                 (5 imágenes) y ejecuta la acción de su clase.
  5. REPORTE     Vuelve al centro, guarda fotos y registro (registros/) y opcionalmente avisa por Telegram.

Uso:
    python3 torreta_ia.py --ver                 # en la Raspberry, con ventana (HDMI o VNC)
    python3 torreta_ia.py                       # sin ventana (arranque automático con systemd)
    python3 torreta_ia.py --solo-vision --ver   # solo clasifica en vivo y mide latencia/FPS (para el informe)
    python3 torreta_ia.py --sim --ver           # en el PC con webcam: sin servos ni GPIO (Enter o espacio = botón)
Mantener el botón 3 s (o 'q' en la ventana) apaga la torreta.
"""
import argparse
import csv
import os
import threading
import time
from collections import Counter

import cv2

import hardware
import vision
from clasificador import Clasificador

AQUI = os.path.dirname(os.path.abspath(__file__))
MODELO = os.path.join(AQUI, "modelo", "modelo_torreta.tflite")
ETIQUETAS = os.path.join(AQUI, "modelo", "etiquetas.txt")
REGISTROS = os.path.join(AQUI, "registros")

# Cámara OV5647 / Pi Camera v1.3: campo de visión aproximado
FOV_H, FOV_V = 53.5, 41.4
GRADOS_PX = FOV_H / vision.ANCHO
SIGNO_PAN, SIGNO_TILT = -1, 1     # si la torreta corre en sentido contrario al objetivo, cambia el signo
KP = 0.45                         # fracción del error angular que se corrige en cada imagen
ZONA_CENTRADO = 2.5               # grados: dentro de esta zona se considera centrado
BARRIDO_PAN = [25, 55, 90, 125, 155]
BARRIDO_TILT = [90]               # para cubrir más altura: [75, 100]
UMBRAL = 0.80                     # confianza mínima; por debajo la figura es "desconocido"
VOTOS = 5                         # imágenes para confirmar la clase antes de actuar
MAX_FIGURAS = 6                   # máximo de figuras clasificadas por imagen
RADIO_FUSION = 4.0                # grados: dos detecciones del barrido más cerca que esto son el mismo objetivo
RADIO_MIRA = 6.0                  # grados: al confirmar, solo cuenta la figura que esté así de cerca del centro

# Identificación amigo-enemigo: cada clase tiene un rol, una prioridad y una acción distinta.
CLASES = {
    "triangulo": {"rol": "MISIL",           "prioridad": 1, "color_bgr": (0, 0, 255),
                  "accion": "Alarma + seguimiento 2 s + rafaga de 3 disparos"},
    "cuadrado":  {"rol": "AVION ENEMIGO",   "prioridad": 2, "color_bgr": (0, 128, 255),
                  "accion": "Dos pitidos + seguimiento 2 s + 1 disparo"},
    "estrella":  {"rol": "DRON",            "prioridad": 3, "color_bgr": (0, 220, 255),
                  "accion": "Tono de advertencia + vigilancia 4 s sin disparo"},
    "circulo":   {"rol": "ALIADO",          "prioridad": 4, "color_bgr": (0, 200, 0),
                  "accion": "Melodia + asiente con la cabeza (no dispara)"},
    "cruz":      {"rol": "CIVIL/MEDICO",    "prioridad": 5, "color_bgr": (255, 0, 160),
                  "accion": "Tono grave + niega con la cabeza (disparo bloqueado)"},
}


class Torreta:
    def __init__(self, a):
        self.a = a
        sim = a.sim
        self.cam = vision.Camara(usb=a.usb or sim)
        self.clf = Clasificador(MODELO, ETIQUETAS, umbral=UMBRAL)
        self.servos = hardware.Servos(sim)
        self.buzzer = hardware.Buzzer(sim)
        self.led = hardware.Led(sim)
        self.boton = hardware.Boton(sim)
        self.estado = "ESPERA"
        faltan = [c for c in CLASES if c not in self.clf.etiquetas]
        if faltan:
            print(f"AVISO: el modelo no tiene las clases {faltan}. Etiquetas del modelo: {self.clf.etiquetas}")

    # ---------- visión ----------
    def leer(self):
        for _ in range(5):
            f = self.cam.leer()
            if f is not None:
                return f
        raise RuntimeError("La cámara no entrega imágenes")

    def clasificar(self, frame):
        figuras = vision.localizar(frame)[:MAX_FIGURAS]
        for f in figuras:
            f["clase"], f["conf"], _ = self.clf.predecir(vision.recortar(frame, f["caja"]))
        return figuras

    def mostrar(self, frame, figuras, texto=""):
        """Dibuja y muestra la imagen (si --ver). También atiende el teclado en simulación."""
        if not self.a.ver:
            return
        vista = frame.copy()
        for f in figuras:
            x, y, w, h = f["caja"]
            info = CLASES.get(f.get("clase"))
            col = info["color_bgr"] if info else (160, 160, 160)
            cv2.rectangle(vista, (x, y), (x + w, y + h), col, 2)
            etiqueta = f"{f.get('clase', '?')} {f.get('conf', 0):.0%}"
            if info:
                etiqueta += f" - {info['rol']}"
            cv2.putText(vista, etiqueta, (x, max(15, y - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, col, 2)
        c = (vision.ANCHO // 2, vision.ALTO // 2)
        cv2.drawMarker(vista, c, (255, 255, 255), cv2.MARKER_CROSS, 30, 2)
        cv2.circle(vista, c, int(ZONA_CENTRADO / GRADOS_PX), (255, 255, 255), 1)
        cv2.rectangle(vista, (0, 0), (vision.ANCHO, 32), (0, 0, 0), -1)
        cv2.putText(vista, f"{self.estado}  pan {self.servos.pan:.0f}  tilt {self.servos.tilt:.0f}  "
                           f"IA {self.clf.ultima_latencia_ms:.0f} ms  {texto}",
                    (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
        if self.estado == "ESPERA":
            cv2.putText(vista, "Oprima el boton para iniciar", (120, vision.ALTO - 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
        cv2.imshow("Torreta CIWS - IA", vista)
        k = cv2.waitKey(1) & 0xFF
        if k == ord(" "):
            self.boton.simular_pulso()
        elif k == ord("q"):
            self.boton.apagar_pedido.set()
        return vista

    def angulo_de(self, centro):
        """Ángulos (pan, tilt) a los que hay que ir para tener ese píxel en el centro."""
        dx = (centro[0] - vision.ANCHO / 2) * GRADOS_PX
        dy = (centro[1] - vision.ALTO / 2) * GRADOS_PX
        return self.servos.pan + SIGNO_PAN * dx, self.servos.tilt + SIGNO_TILT * dy

    # ---------- etapas del ciclo ----------
    def barrido(self):
        """Recorre el campo y devuelve los objetivos encontrados (fusionando los vistos desde dos posiciones)."""
        self.estado = "BARRIDO"
        self.led.parpadear("blanco", 0.3)
        objetivos = []
        for tilt in BARRIDO_TILT:
            for pan in BARRIDO_PAN:
                self.servos.ir_a(pan, tilt)
                time.sleep(0.35)                       # deja que se quiete la imagen
                for _ in range(3):
                    frame = self.leer()
                    figuras = self.clasificar(frame)
                    self.mostrar(frame, figuras, f"objetivos: {len(objetivos)}")
                    for f in figuras:
                        if f["clase"] not in CLASES:
                            continue
                        p, t = self.angulo_de(f["centro"])
                        for o in objetivos:
                            if abs(o["pan"] - p) < RADIO_FUSION and abs(o["tilt"] - t) < RADIO_FUSION:
                                o["votos"][f["clase"]] += 1
                                n = sum(o["votos"].values())
                                o["pan"] += (p - o["pan"]) / n
                                o["tilt"] += (t - o["tilt"]) / n
                                break
                        else:
                            objetivos.append({"pan": p, "tilt": t, "votos": Counter({f["clase"]: 1})})
        for o in objetivos:
            o["clase"] = o["votos"].most_common(1)[0][0]
        objetivos.sort(key=lambda o: CLASES[o["clase"]]["prioridad"])
        return objetivos

    def seguir(self, clase, duracion, bloquear=False):
        """Sigue la figura de esa clase moviendo pan/tilt. Si bloquear=True, sale apenas queda centrada.
        Devuelve (centrada, frame, figura)."""
        fin = time.time() + duracion
        centrada, frame, objetivo = 0, None, None
        while time.time() < fin:
            frame = self.leer()
            figuras = self.clasificar(frame)
            cands = [f for f in figuras if f["clase"] == clase]
            if cands:
                c = (vision.ANCHO / 2, vision.ALTO / 2)
                objetivo = min(cands, key=lambda f: (f["centro"][0] - c[0]) ** 2 + (f["centro"][1] - c[1]) ** 2)
                ex = (objetivo["centro"][0] - c[0]) * GRADOS_PX
                ey = (objetivo["centro"][1] - c[1]) * GRADOS_PX
                if abs(ex) < ZONA_CENTRADO and abs(ey) < ZONA_CENTRADO:
                    centrada += 1
                    if bloquear and centrada >= 3:
                        self.mostrar(frame, figuras, "BLOQUEADO")
                        return True, frame, objetivo
                else:
                    centrada = 0
                    self.servos.mover(SIGNO_PAN * KP * ex, SIGNO_TILT * KP * ey)
            self.mostrar(frame, figuras, f"siguiendo {clase}")
        return centrada > 0, frame, objetivo

    def confirmar(self, objetivo):
        """Votación sobre varias imágenes: evita actuar por un error de una sola imagen."""
        votos, confs = Counter(), []
        for _ in range(VOTOS):
            frame = self.leer()
            figuras = self.clasificar(frame)
            self.mostrar(frame, figuras, "confirmando")
            if not figuras:
                continue
            c = (vision.ANCHO / 2, vision.ALTO / 2)
            f = min(figuras, key=lambda f: (f["centro"][0] - c[0]) ** 2 + (f["centro"][1] - c[1]) ** 2)
            if max(abs(f["centro"][0] - c[0]), abs(f["centro"][1] - c[1])) * GRADOS_PX > RADIO_MIRA:
                continue                            # lo que está en la mira no es este objetivo
            votos[f["clase"]] += 1
            confs.append(f["conf"])
        if not votos:
            return None, 0.0
        clase, n = votos.most_common(1)[0]
        if clase not in CLASES or n < (VOTOS // 2 + 1):
            return None, 0.0
        return clase, sum(confs) / len(confs)

    def accion(self, clase):
        """Una acción diferente por clase (requisito de la rúbrica)."""
        s, b, l = self.servos, self.buzzer, self.led
        if clase == "triangulo":
            l.parpadear("rojo", 0.15)
            b.alarma()
            self.seguir(clase, 2.0)
            s.disparar(3)
        elif clase == "cuadrado":
            l.color("naranja")
            b.dos_pitidos()
            self.seguir(clase, 2.0)
            s.disparar(1)
        elif clase == "estrella":
            l.parpadear("amarillo", 0.6)
            b.subida()
            self.seguir(clase, 4.0)
        elif clase == "circulo":
            l.color("verde")
            b.aliado()
            s.asentir()
        elif clase == "cruz":
            l.color("morado")
            b.grave()
            s.negar()
        time.sleep(0.4)

    def enfrentar(self, objetivos, carpeta, ciclo):
        resultados = []
        for i, o in enumerate(objetivos, 1):
            info = CLASES[o["clase"]]
            self.estado = f"OBJETIVO {i}/{len(objetivos)}"
            print(f"[{i}/{len(objetivos)}] {o['clase']} ({info['rol']}) visto en pan={o['pan']:.0f} tilt={o['tilt']:.0f}")
            self.led.color("blanco")
            self.servos.ir_a(o["pan"], o["tilt"])
            ok, frame, _ = self.seguir(o["clase"], 3.0, bloquear=True)
            if not ok:
                print("   no se pudo centrar; se intenta confirmar igual")
            clase, conf = self.confirmar(o)
            if clase is None:
                print("   no se confirmó la clase: se ignora")
                resultados.append([ciclo, i, o["clase"], "-", "no confirmado", 0, round(self.servos.pan), round(self.servos.tilt)])
                continue
            info = CLASES[clase]
            print(f"   confirmado: {clase} ({conf:.0%}) -> {info['accion']}")
            self.estado = f"{info['rol']}"
            frame = self.leer()
            vista = self.mostrar(frame, self.clasificar(frame), info["accion"])
            foto = os.path.join(carpeta, f"{i:02d}_{clase}.jpg")
            cv2.imwrite(foto, vista if vista is not None else frame)
            self.accion(clase)
            resultados.append([ciclo, i, clase, info["rol"], info["accion"], round(conf, 3),
                               round(self.servos.pan), round(self.servos.tilt)])
            telegram(f"Torreta: {info['rol']} ({clase}, {conf:.0%}) - {info['accion']}", foto)
        return resultados

    def ciclo(self):
        ciclo = time.strftime("%Y%m%d_%H%M%S")
        carpeta = os.path.join(REGISTROS, ciclo)
        os.makedirs(carpeta, exist_ok=True)
        t0 = time.time()
        print(f"\n=== Ciclo {ciclo} ===")
        self.buzzer.inicio()
        objetivos = self.barrido()
        print(f"Barrido: {len(objetivos)} objetivo(s): " + ", ".join(o["clase"] for o in objetivos))
        resultados = self.enfrentar(objetivos, carpeta, ciclo)
        self.estado = "REGRESO"
        self.led.color("blanco")
        self.servos.ir_a(90, 90)
        self.buzzer.fin()
        historial = os.path.join(REGISTROS, "historial.csv")
        nuevo = not os.path.exists(historial)
        with open(historial, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if nuevo:
                w.writerow(["ciclo", "n", "clase", "rol", "accion", "confianza", "pan", "tilt"])
            w.writerows(resultados)
        resumen = Counter(r[2] for r in resultados)
        print(f"Ciclo terminado en {time.time() - t0:.1f} s. Resumen: {dict(resumen)}. Fotos en {carpeta}")

    def espera(self):
        self.estado = "ESPERA"
        self.led.parpadear("azul", 1.5)
        print("\nListo. Oprima el botón para iniciar (mantener 3 s = apagar).")
        while not self.boton.apagar_pedido.is_set():
            if self.boton.fue_pulsado():
                return True
            if self.a.ver:                               # vista previa en vivo mientras espera
                frame = self.leer()
                self.mostrar(frame, self.clasificar(frame))
            else:
                time.sleep(0.05)
        return False

    def solo_vision(self):
        """Clasificación en vivo sin mover nada. Mide latencia del modelo y FPS (datos para el informe)."""
        self.estado = "SOLO VISION"
        lat, t0, n = [], time.time(), 0
        while not self.boton.apagar_pedido.is_set():
            frame = self.leer()
            figuras = self.clasificar(frame)
            if figuras:
                lat.append(self.clf.ultima_latencia_ms)
            n += 1
            fps = n / (time.time() - t0)
            self.mostrar(frame, figuras, f"{fps:.1f} FPS")
            if not self.a.ver and n % 30 == 0:
                print(f"{fps:.1f} FPS | " + ", ".join(f"{f['clase']} {f['conf']:.0%}" for f in figuras))
        if lat:
            lat.sort()
            print(f"Latencia del modelo: media {sum(lat) / len(lat):.1f} ms, "
                  f"p95 {lat[int(0.95 * (len(lat) - 1))]:.1f} ms, {n / (time.time() - t0):.1f} FPS totales")

    def apagar(self):
        self.led.color("apagado")
        self.servos.apagar()
        self.buzzer.apagar()
        self.led.apagar()
        self.cam.cerrar()
        cv2.destroyAllWindows()


def telegram(texto, foto=None):
    """Aviso opcional (como el correo del ejemplo de la rúbrica). Se activa con las variables de entorno
    TORRETA_TELEGRAM_TOKEN y TORRETA_TELEGRAM_CHAT. Se envía en segundo plano para no frenar la torreta."""
    token, chat = os.environ.get("TORRETA_TELEGRAM_TOKEN"), os.environ.get("TORRETA_TELEGRAM_CHAT")
    if not token or not chat:
        return

    def enviar():
        try:
            import requests
            url = f"https://api.telegram.org/bot{token}/"
            if foto:
                with open(foto, "rb") as f:
                    requests.post(url + "sendPhoto", data={"chat_id": chat, "caption": texto}, files={"photo": f}, timeout=15)
            else:
                requests.post(url + "sendMessage", data={"chat_id": chat, "text": texto}, timeout=15)
        except Exception as e:                     # sin internet la torreta sigue funcionando
            print(f"   (Telegram no disponible: {e})")

    threading.Thread(target=enviar, daemon=True).start()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ver", action="store_true", help="mostrar ventana con lo que ve la torreta")
    ap.add_argument("--usb", action="store_true", help="webcam USB en vez de la Pi Camera")
    ap.add_argument("--sim", action="store_true", help="simulación en el PC: sin servos, buzzer, LED ni botón reales")
    ap.add_argument("--solo-vision", action="store_true", help="solo clasificar en vivo y medir latencia")
    a = ap.parse_args()

    t = Torreta(a)
    try:
        if a.solo_vision:
            t.solo_vision()
        else:
            while t.espera():
                t.ciclo()
    except KeyboardInterrupt:
        pass
    finally:
        print("Apagando torreta...")
        t.apagar()


if __name__ == "__main__":
    main()
