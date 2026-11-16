# Carpeta del modelo

Aquí van los dos archivos que descarga el notebook `entrenamiento/Entrenamiento_Torreta_IA.ipynb` al final:

- `modelo_torreta.tflite`: MobileNetV2 entrenado con el dataset propio, convertido a TensorFlow Lite y cuantizado.
- `etiquetas.txt`: una clase por línea, en el orden de salida del modelo.

`torreta_ia.py` los busca en esta carpeta.
