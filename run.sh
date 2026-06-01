#!/bin/bash
echo "Inicializando Sistema de Inspeção de Túneis (ATR)..."

cleanup() {
    local exit_code=$?
    if [ -n "${PID_CPP:-}" ]; then
        kill "$PID_CPP" 2>/dev/null
    fi
    if [ -n "${PID_SIM:-}" ]; then
        kill "$PID_SIM" 2>/dev/null
    fi
    if [ -n "${PID_YOLO:-}" ]; then
        kill "$PID_YOLO" 2>/dev/null
    fi
    exit "$exit_code"
}

trap cleanup EXIT INT TERM

# 0. Garante que o script rode a partir da raiz do projeto, não importando de onde foi chamado
cd "$(dirname "$0")"

if [ -z "${PYTHON:-}" ]; then
    if [ -x "./venv/bin/python" ]; then
        PYTHON="./venv/bin/python"
    else
        PYTHON="python3"
    fi
fi

# 1. Compila o núcleo C++
echo "[1/4] Iniciando Núcleo RTOS C++"
mkdir -p build && cd build
cmake ..
make
cd .. # Volta para a raiz para rodar os scripts em Python

# Procura o executável com o nome correto gerado pelo seu CMake
if [ -f "./build/atr_inspection" ]; then
    EXEC_PATH="./build/atr_inspection"
elif [ -f "./bin/atr_inspection" ]; then
    EXEC_PATH="./bin/atr_inspection"
else
    echo "ERRO: O executável C++ (atr_inspection) não foi encontrado após a compilação."
    exit 1
fi

# Executa o C++ em background
$EXEC_PATH &
PID_CPP=$!

# Aguarda 2 segundos para os buffers e o C++ subirem no MQTT
sleep 2 

# 2. Inicia os serviços Python em background
echo "[2/4] Iniciando Simulador Físico"
"$PYTHON" src/scripts/tunel_simulator.py &
PID_SIM=$!

echo "[3/4] Iniciando YOLOv8 Daemon"
"$PYTHON" src/scripts/yolo_mqtt_service.py &
PID_YOLO=$!

# 3. Inicia a Interface (foreground)
echo "[4/4] Iniciando GUI do Operador"
"$PYTHON" src/scripts/operator_interface.py
