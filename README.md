# Torreta pan-tilt que sigue formas (Raspberry Pi)

Proyecto de **Inteligencia Artificial en Dispositivos Móviles y Embebidos**: una torreta tipo CIWS que usa una cámara en una Raspberry Pi para detectar formas geométricas y seguir con dos servos la forma objetivo.

**Autor:** Juan Camilo Díaz Rangel (2215469)

![Ensamble](Diseño%203D/Imagenes/Ensamble_isometrica.jpg)

## Cómo funciona
1. La Pi Camera captura la imagen (640 × 480).
2. OpenCV la binariza (Otsu), busca contornos y los clasifica por número de vértices (`approxPolyDP`): triángulo, cuadrado, rectángulo, pentágono, hexágono o círculo.
3. Si aparece la forma objetivo, el error entre su centro y el centro de la imagen mueve los servos con un control proporcional. Así se gira (pan) y se inclina (tilt) hasta centrarla.
4. Si la pierde por más de 2 s, hace un barrido lento buscándola.

## Estructura
| Carpeta | Contenido |
|---|---|
| `software/` | `seguidor_formas.py`: visión + control de los servos (PCA9685) |
| `Diseño 3D/SolidWorks/` | Piezas `.SLDPRT` y ensamble `Ensamble/Ensamble_Torreta_PanTilt.SLDASM` (con los SG90, la cámara y los separadores) |
| `Diseño 3D/STL_Impresion/` | Piezas para imprimir: Base, Fork, Head y Adaptador de cámara (~100 g de PLA) |
| `Diseño 3D/Imagenes/` | Vistas del ensamble y de cada pieza |
| `Diseño 3D/scripts/` | Scripts de Python (API de SolidWorks) que importan las piezas y arman el ensamble |
| `Diseño original/` | Archivos STEP/STL del diseño base descargado |
| `Lista_de_compras.md` | Materiales, precios aproximados, montaje y conexiones |

## Hardware
Raspberry Pi 4 o 5 (prestada por la universidad), cámara OV5647 de 5 MP (compatible con la Pi Camera v1.3/v2), 2 servos SG90, driver PCA9685 (I2C), módulo de carga o fuente de 5 V aparte para los servos y tornillería M2/M3. Costo aproximado sin la Pi: 75.000 – 115.000 COP más la alimentación. Detalle en [Lista_de_compras.md](Lista_de_compras.md).

**Conexión PCA9685 → Pi:** VCC → 3.3 V (pin 1), GND → pin 6, SDA → GPIO2 (pin 3), SCL → GPIO3 (pin 5). Servo pan al canal 0 y tilt al canal 1. Los 5 V del módulo de carga van a la bornera V+, con la tierra común con la Pi.

## Uso
```bash
sudo apt install -y python3-picamera2 python3-opencv
pip install adafruit-circuitpython-servokit --break-system-packages
python3 software/seguidor_formas.py --forma triangulo --ver
```
Opciones: `--sin-servos` (prueba solo la visión), `--usb` (webcam USB en vez de la Pi Camera).

## Créditos
Las piezas Base, Fork y Head son del diseño *"Pan-Tilt Camera Turret for 9g Servos (SG90)"*, descargado de internet (archivos sin cambios en `Diseño original/`). El adaptador de la cámara, el ensamble y el software son de este proyecto.
