#!/bin/bash

# Função para capturar o encerramento e limpar a memória
cleanup() {
    echo ""
    echo "========================================="
    echo "  Encerrando todos os sistemas ATR...    "
    echo "========================================="
    # O comando 'kill 0' envia o sinal SIGTERM para todos os processos
    # que foram iniciados por este script (o grupo de processos atual).
    kill 0
    exit 0
}

# Associa a função cleanup aos sinais SIGINT (CTRL+C) e SIGTERM
trap cleanup SIGINT SIGTERM

echo "========================================="
echo "  Inicializando Sistema de Inspeção ATR  "
echo "========================================="

# Passo 1: Compilar o código C++
echo "[1/5] Compilando o núcleo C++..."
make clean && make
if [ $? -ne 0 ]; then
    echo "Erro na compilação do C++. Abortando a execução."
    exit 1
fi

# Passo 2: Iniciar o serviço MQTT do YOLO
echo "[2/5] Iniciando o Serviço IA (YOLOv8) em background..."
python3 src/scripts/yolo_mqtt_service.py &
sleep 3 # Dá tempo para a IA carregar o modelo PyTorch na RAM

# Passo 3: Iniciar o Simulador do Túnel
echo "[3/5] Iniciando o Simulador Físico 2D em background..."
python3 src/scripts/simulador_tunel.py &
sleep 1

# Passo 4: Iniciar o Núcleo C++
echo "[4/5] Iniciando o Cérebro do Robô (C++) em background..."
./bin/inspection_robot &
sleep 1

# Passo 5: Iniciar a Interface de Operação Remota
# Note que este não tem o '&' no final. Ele roda em foreground.
echo "[5/5] Abrindo a Interface de Operação Remota..."
python3 src/scripts/interface_operador.py

# Se o usuário fechar a janela da interface gráfica, o script chega aqui
# e nós forçamos a limpeza dos processos que estão em background
cleanup