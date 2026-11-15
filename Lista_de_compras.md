# Torreta pan-tilt con Raspberry Pi: lista de compras

Proyecto de IA en embebidos: una torreta tipo CIWS que detecta formas con la cámara y sigue la forma correcta moviendo 2 servos.
Diseño: "Pan-Tilt Camera Turret for 9g Servos (SG90)" (Base, Fork y Head) + adaptador de cámara hecho por Claude.

Los precios son **aproximados** (Colombia, tiendas de electrónica o MercadoLibre, noviembre de 2026). Confírmalos en la tienda.

## Lo esencial

| # | Qué | Cant. | Para qué | Precio aprox. (COP) |
|---|-----|-------|----------|---------------------|
| 1 | Raspberry Pi 4 Model B de 4 GB (o una Pi 5) | 1 | El cerebro: corre OpenCV y controla los servos | 250.000 – 350.000 (si la universidad no la presta) |
| 2 | Tarjeta microSD de 32 GB, clase 10 / A1 | 1 | Sistema operativo (Raspberry Pi OS) | 20.000 – 35.000 |
| 3 | Fuente USB-C de 5 V y 3 A (Pi 4) o de 5 V y 5 A (Pi 5) | 1 | Alimentar la Raspberry | 30.000 – 60.000 |
| 4 | Cámara Raspberry Pi Camera Module v2 (8 MP) o Module 3 | 1 | Ver las formas. El adaptador impreso está hecho para sus agujeros (21 × 12.5 mm, M2) | 80.000 – 150.000 |
| 5 | **Solo si es Pi 5:** cable de cámara de 22 a 15 pines (200 a 300 mm) | 1 | La Pi 5 usa un conector más pequeño | 10.000 – 20.000 |
| 6 | Servo SG90 de 9 g (o MG90S, que mide lo mismo y tiene engranajes metálicos) | 3 | 2 para la torreta (giro e inclinación) y 1 de repuesto | 8.000 – 15.000 c/u |
| 7 | Módulo PCA9685 (driver de 16 servos, I2C) | 1 | Genera un PWM estable. Con el PWM por software de la Pi, los servos tiemblan | 15.000 – 25.000 |
| 8 | Fuente aparte de 5 V y 2–3 A para los servos (adaptador con jack DC y bornera) | 1 | Los servos no se alimentan desde la Pi. Hay que unir las tierras (GND) | 15.000 – 30.000 |
| 9 | Cables dupont hembra-hembra y macho-hembra (kit de 40) | 1 | Conexiones Pi ↔ PCA9685 | 8.000 – 12.000 |

## Tornillería (para el adaptador de la cámara)

| Qué | Cant. | Dónde va |
|-----|-------|----------|
| Tornillo M3 × 12 mm con tuerca (compra también 4 de 16 mm por si la pared del Head es más gruesa) | 4 | Adaptador al frente del Head (las cabezas quedan hundidas en el adaptador) |
| Tornillo M2 × 10 mm con tuerca | 4 | Cámara al adaptador |
| Separador (standoff) M2 de 3 mm, o 2 tuercas M2 por tornillo | 4 | Entre el adaptador y la cámara, para no aplastar los componentes de atrás |
| Tornillos de los servos | — | Vienen en la bolsita del SG90 |

Sugerencia: un kit de separadores de nylon M2/M2.5/M3 (unos 20.000 COP) trae casi todo esto.

## Impresión 3D

- Filamento PLA: unos **100 g** para las 4 piezas (volumen sólido total ≈ 154 cm³, impreso al 20–30 % de relleno).
- Piezas en `Diseño 3D\STL_Impresion\`: `01_Base`, `02_Fork`, `03_Head` y `04_Adaptador_Camara`.
- Si no tienes impresora, en el laboratorio o en un servicio de impresión cuesta más o menos 30.000 – 60.000 COP.

## Opcionales (recomendados)

- Disipadores o ventilador para la Raspberry: OpenCV corriendo todo el tiempo la calienta (10.000 – 25.000).
- Pegante instantáneo (Super Bonder) para fijar los cuernos de los servos en la Base y en el brazo del Fork.
- Protoboard pequeña y un condensador de 470–1000 µF en la alimentación de los servos, para que no se reinicie nada cuando arrancan.
- Un láser de 5 mW o un LED indicador montado en el Head, para "marcar" la forma que se está siguiendo.

## Cómo se arma (resumen)

1. **Servo de giro (pan):** va boca abajo dentro del bolsillo de abajo del Fork, atornillado por las orejas. Su cuerno largo se pega en la ranura del centro de la Base.
2. **Servo de inclinación (tilt):** va dentro del Head, con el eje hacia el brazo grueso del Fork. Su cuerno largo se encaja en la ranura del brazo. Al otro lado, el pivote del Head entra en el agujero del brazo delgado.
3. **Cámara:** adaptador al frente del Head con 4 M3, y la cámara sobre el adaptador con 4 M2 y separadores de 3 mm.
4. **Conexiones:** PCA9685 a la Pi por I2C (SDA = GPIO2 / pin 3, SCL = GPIO3 / pin 5, VCC = 3.3 V / pin 1, GND = pin 6). Los servos van a los canales 0 y 1. La fuente de 5 V de los servos va a la bornera V+ del PCA9685, y las tierras quedan unidas.

**Antes de pegar los cuernos**, centra los servos en 90°. Así la torreta arranca mirando al frente.

## Software (idea)

- Raspberry Pi OS de 64 bits, `picamera2` + `opencv-python`, y `adafruit-circuitpython-servokit` para el PCA9685.
- Detección de formas: umbral o color → `findContours` → `approxPolyDP` (3 vértices = triángulo, 4 = cuadrado, muchos = círculo).
- Seguimiento: el error entre el centro de la forma y el centro de la imagen mueve los servos (control P o PI).
