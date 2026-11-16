"""Clasificador TFLite (MobileNetV2 entrenado en Colab con Entrenamiento_Torreta_IA.ipynb).

El modelo trae dentro la normalización (Rescaling), así que aquí solo se le pasa la imagen RGB
en 0-255 como float32. No hay que dividir por 255 ni restar medias: así no se repite el error del
notebook de tapabocas, que normalizaba distinto al entrenar y al predecir.
"""
import os
import time

import cv2
import numpy as np


def _cargar_interprete(ruta):
    try:
        from ai_edge_litert.interpreter import Interpreter       # LiteRT (reemplazo oficial de tflite-runtime)
    except ImportError:
        try:
            from tflite_runtime.interpreter import Interpreter
        except ImportError:
            from tensorflow.lite import Interpreter              # en el PC, si está TensorFlow completo
    return Interpreter(model_path=ruta, num_threads=4)


class Clasificador:
    def __init__(self, ruta_modelo, ruta_etiquetas, umbral=0.80):
        if not os.path.exists(ruta_modelo):
            raise FileNotFoundError(f"No encuentro el modelo {ruta_modelo}. Entrénalo en Colab y copia "
                                    "modelo_torreta.tflite y etiquetas.txt a software/modelo/")
        self.interp = _cargar_interprete(ruta_modelo)
        self.interp.allocate_tensors()
        self.ent = self.interp.get_input_details()[0]
        self.sal = self.interp.get_output_details()[0]
        _, self.alto, self.ancho, _ = self.ent["shape"]
        with open(ruta_etiquetas, encoding="utf-8") as f:
            self.etiquetas = [l.strip() for l in f if l.strip()]
        self.umbral = umbral
        self.ultima_latencia_ms = 0.0

    def predecir(self, recorte_bgr):
        """Devuelve (clase, confianza, vector_de_probabilidades). Si la confianza es baja, la clase es 'desconocido'."""
        img = cv2.cvtColor(recorte_bgr, cv2.COLOR_BGR2RGB)          # la cámara da BGR; el modelo se entrenó en RGB
        img = cv2.resize(img, (self.ancho, self.alto), interpolation=cv2.INTER_AREA)
        x = np.expand_dims(img.astype(np.float32), 0)
        if self.ent["dtype"] == np.uint8:                             # por si se exporta un modelo int8 completo
            esc, cero = self.ent["quantization"]
            x = np.clip(x / esc + cero, 0, 255).astype(np.uint8)
        t0 = time.perf_counter()
        self.interp.set_tensor(self.ent["index"], x)
        self.interp.invoke()
        p = self.interp.get_tensor(self.sal["index"])[0].astype(np.float32)
        self.ultima_latencia_ms = (time.perf_counter() - t0) * 1000
        if self.sal["dtype"] == np.uint8:
            esc, cero = self.sal["quantization"]
            p = (p - cero) * esc
        i = int(np.argmax(p))
        clase = self.etiquetas[i] if p[i] >= self.umbral else "desconocido"
        return clase, float(p[i]), p
