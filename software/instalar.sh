#!/bin/bash
# Instala todo lo de la torreta en Raspberry Pi OS (Bookworm, 64 bits) y deja el arranque automático.
# Uso:  cd software && bash instalar.sh
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="$HOME/torreta-venv"

echo "== Paquetes del sistema =="
sudo apt update
sudo apt install -y python3-picamera2 python3-opencv python3-gpiozero python3-lgpio python3-venv i2c-tools

echo "== Activando I2C (PCA9685) =="
sudo raspi-config nonint do_i2c 0

echo "== Entorno de Python (usa picamera2 y OpenCV del sistema) =="
python3 -m venv --system-site-packages "$VENV"
# Se fija la versión de numpy del sistema para no romper OpenCV ni picamera2.
NP=$(python3 -c "import numpy; print(numpy.__version__)")
echo "numpy==$NP" > /tmp/torreta_restricciones.txt
"$VENV/bin/pip" install -c /tmp/torreta_restricciones.txt adafruit-circuitpython-servokit requests
"$VENV/bin/pip" install -c /tmp/torreta_restricciones.txt ai-edge-litert \
  || "$VENV/bin/pip" install -c /tmp/torreta_restricciones.txt tflite-runtime

echo "== Revisando el PCA9685 (debe aparecer 40) =="
sudo i2cdetect -y 1 || true

echo "== Servicio para que la torreta arranque sola al encender =="
sudo tee /etc/systemd/system/torreta.service > /dev/null <<EOF
[Unit]
Description=Torreta CIWS con IA
After=multi-user.target

[Service]
User=$USER
WorkingDirectory=$DIR
EnvironmentFile=-$HOME/.torreta_env
ExecStart=$VENV/bin/python $DIR/torreta_ia.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload

echo
echo "Listo. Pasos siguientes:"
echo "  1. Copia modelo_torreta.tflite y etiquetas.txt (salen de Colab) a $DIR/modelo/"
echo "  2. Prueba:            $VENV/bin/python torreta_ia.py --ver"
echo "  3. Arranque solo:     sudo systemctl enable --now torreta"
echo "  4. (Opcional) Telegram: crea ~/.torreta_env con TORRETA_TELEGRAM_TOKEN=... y TORRETA_TELEGRAM_CHAT=..."
