# Torreta pan-tilt con Raspberry Pi: lista de compras

Proyecto de IA en embebidos: una torreta tipo CIWS que detecta formas con la cámara y sigue la forma correcta moviendo 2 servos.
Diseño: "Pan-Tilt Camera Turret for 9g Servos (SG90)" (Base, Fork y Head) + adaptador de cámara hecho por Claude.

Los precios son **aproximados** (Colombia, tiendas de electrónica o MercadoLibre, noviembre de 2026) y no se confirmaron en una tienda. Confírmalos antes de comprar.

## Lo esencial (versión económica)

La **Raspberry Pi la presta la universidad**, así que no se compra. Pide con ella su fuente USB-C y, si se puede, la microSD.

| # | Qué | Cant. | Para qué | Precio aprox. (COP) |
|---|-----|-------|----------|---------------------|
| 1 | Raspberry Pi 4 o 5 | 1 | El cerebro: corre OpenCV y controla los servos | **0 (prestada)** |
| 2 | Tarjeta microSD de 32 GB, A1 (de cualquier marca conocida) | 1 | Sistema operativo. Si te prestan una o ya tienes, 0 | 15.000 – 22.000 |
| 3 | Cámara **OV5647 de 5 MP** (compatible con la Pi Camera v1.3, con su cable plano) | 1 | Ver las formas. Tiene los mismos agujeros M2 que la v2 (21 × 12.5 mm), así que el adaptador impreso sirve. Para OpenCV a 640×480 alcanza de sobra | 25.000 – 40.000 |
| 4 | **Solo si es Pi 5:** cable de cámara de 22 a 15 pines (200 mm) | 1 | La Pi 5 usa un conector más pequeño | 8.000 – 15.000 |
| 5 | Servo SG90 de 9 g | 2 | Giro (pan) e inclinación (tilt). El repuesto es opcional | 7.000 – 10.000 c/u |
| 6 | Módulo PCA9685 (16 canales, I2C) | 1 | PWM estable para los servos; el programa `seguidor_formas.py` lo usa | 15.000 – 22.000 |
| 7 | Cables dupont hembra-hembra (tira de 20) | 1 | Conexiones Pi ↔ PCA9685 | 4.000 – 6.000 |
| 8 | Módulo de carga / alimentación (ver la sección siguiente) | 1 | Alimentar servos (y la Pi si se quiere portátil) | 0 – 60.000 |

**Total aproximado sin el módulo de carga: 75.000 – 115.000 COP** (antes era de 450.000 a 700.000 contando la Raspberry y la Pi Camera v2).

### Lo que se agrega para la versión con IA (Miniproyecto 3)

La rúbrica pide **mínimo 3 actuadores** (los LEDs no cuentan), **un botón que haga todo el ciclo** y **una acción por clase**:

| # | Qué | Cant. | Para qué | Precio aprox. (COP) |
|---|-----|-------|----------|---------------------|
| 9 | Servo SG90 adicional | 1 | **Gatillo** (3.er actuador): va pegado al costado del Head y mueve un brazo o bandera de "disparo". PCA9685 canal 2 | 7.000 – 10.000 |
| 10 | Módulo **buzzer pasivo** KY-006 (pasivo, no activo: tiene que poder hacer tonos distintos) | 1 | 4.º actuador: un sonido distinto por clase. GPIO18 | 3.000 – 5.000 |
| 11 | Pulsador grande (tipo arcade de 24–30 mm o pulsador de panel) | 1 | Botón de inicio del ciclo. GPIO17 | 3.000 – 8.000 |
| 12 | LED RGB de cátodo común (5 mm) + 3 resistencias de 220 Ω | 1 | Indicador complementario del estado y de la clase | 1.500 – 3.000 |
| 13 | Protoboard pequeña (400 puntos) | 1 | Botón, buzzer y LED | 5.000 – 8.000 |
| 14 | Condensador electrolítico de 1000 µF / 16 V | 1 | Entre V+ y GND del PCA9685: 3 servos arrancando a la vez hacen caer el voltaje | 1.000 – 2.000 |
| 15 | Cartón paja o icopor blanco de ~50 × 70 cm | 1 | Tablero donde se pegan las figuras impresas en la demostración | 3.000 – 6.000 |

**Adicional para la versión con IA: 23.500 – 42.000 COP.**

Ahorros frente a la lista anterior:
- La Raspberry se pide prestada (ahorra 250.000 – 350.000).
- La cámara OV5647 en lugar de la Pi Camera v2/v3 (ahorra 50.000 – 110.000). Una webcam USB que ya tengas también sirve, pero el adaptador impreso está hecho para la cámara de Raspberry y en el programa habría que cambiar `picamera2` por `cv2.VideoCapture(0)`.
- 2 servos en lugar de 3 y una sola tira de cables.
- La fuente de 5 V aparte para los servos se reemplaza por el módulo de carga.

## Módulo de carga (alimentación)

Los servos **no** se alimentan de la Pi: necesitan 5 V aparte, con la tierra (GND) unida a la de la Pi. Opciones de la más barata a la más completa:

| Opción | Qué comprar | Para qué sirve | Precio aprox. (COP) |
|---|---|---|---|
| **A. Cargador de celular que ya tengas** | Nada: un cargador USB de 5 V y 2 A + un cable USB viejo pelado a la bornera V+ del PCA9685 | Torreta en la mesa, conectada a la pared. La Pi va con su fuente prestada | **0 – 5.000** |
| **B. Power bank (recomendada si quieres que sea portátil)** | Power bank de 10.000 mAh con **2 salidas** y al menos 2.4 A (mejor con USB-C PD de 3 A) | Una salida a la Pi y otra a los servos. Se carga con cualquier cargador. Es la opción portátil más segura: ya trae la protección y el circuito de carga | 40.000 – 70.000 (0 si ya tienes una) |
| **C. Batería armada con 18650 (2S)** | 2 celdas 18650 (de marca, no "9900 mAh") + porta pilas 2S + BMS 2S de 5–10 A + convertidor reductor **XL4015 o LM2596** ajustado a 5.1 V + cargador 2S de 8.4 V (o módulo de carga 2S USB-C) | Da más corriente (3–5 A) para la Pi 4 y los servos juntos; sirve para explicar en el informe el sistema de energía | 50.000 – 75.000 en total |
| **D. Módulo 1S tipo power bank** | 1–2 celdas 18650 en paralelo + módulo de carga y elevador **IP5306** (5 V, 2.1 A) | Barato y pequeño, pero 2.1 A queda justo: alcanza para los servos o para una Pi 4 sin cámara funcionando a tope, no para las dos cosas | 20.000 – 35.000 |
| E. UPS HAT para Raspberry (Waveshare, Geekworm X728/X1201) | El HAT + celdas 18650 | Muy cómodo, pero caro y hay que importarlo | 100.000 – 380.000 |

**Recomendación:** si la torreta se presenta en la mesa, opción **A** (gratis). Si debe ser portátil, opción **B** con un power bank de 2 salidas. La **C** solo si el profesor pide diseñar la alimentación.

Cuidados:
- **No uses TP4056 + MT3608** para la Pi: el MT3608 no entrega los 3 A que pide la Pi 4 y se reinicia.
- Pon un condensador de 470–1000 µF entre V+ y GND del PCA9685 para que los servos no hagan caer el voltaje al arrancar.
- Con 18650 sueltas, usa siempre el BMS y no cargues las celdas sin vigilancia.

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
4. **Conexiones:** PCA9685 a la Pi por I2C (SDA = GPIO2 / pin 3, SCL = GPIO3 / pin 5, VCC = 3.3 V / pin 1, GND = pin 6). Los servos van a los canales 0 y 1. Los 5 V del módulo de carga van a la bornera V+ del PCA9685, y las tierras quedan unidas.

**Antes de pegar los cuernos**, centra los servos en 90°. Así la torreta arranca mirando al frente.

## Software (idea)

- Raspberry Pi OS de 64 bits, `picamera2` + `opencv-python`, y `adafruit-circuitpython-servokit` para el PCA9685.
- Detección de formas: umbral o color → `findContours` → `approxPolyDP` (3 vértices = triángulo, 4 = cuadrado, muchos = círculo).
- Seguimiento: el error entre el centro de la forma y el centro de la imagen mueve los servos (control P o PI).
