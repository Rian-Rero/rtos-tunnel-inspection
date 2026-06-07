#!/bin/bash
echo "Inicializando Sistema de Inspeção de Túneis (ATR)..."

PIDS=()
PID_CPP=""
PID_MONITOR=""

cleanup() {
    local exit_code=$?
    # Ignora novos sinais durante o cleanup (segundo Ctrl+C não interrompe)
    trap '' EXIT INT TERM

    echo ""
    echo "Encerrando sistema..."

    # Agrupa todos os PIDs filhos
    local all_pids=()
    [ -n "$PID_CPP"     ] && all_pids+=("$PID_CPP")
    [ -n "$PID_MONITOR" ] && all_pids+=("$PID_MONITOR")
    for p in "${PIDS[@]}"; do
        [ "$p" != "$PID_CPP" ] && all_pids+=("$p")
    done

    # 1) SIGTERM → dá chance de shutdown gracioso (C++ faz join() e flush do CSV)
    for pid in "${all_pids[@]}"; do
        kill -TERM "$pid" 2>/dev/null
    done

    # 2) Aguarda até 3 s — necessário para o C++ encerrar threads e fechar o CSV
    local deadline=$(( SECONDS + 3 ))
    while [ $SECONDS -lt $deadline ]; do
        local alive=false
        for pid in "${all_pids[@]}"; do
            kill -0 "$pid" 2>/dev/null && alive=true && break
        done
        $alive || break
        sleep 0.2
    done

    # 3) SIGKILL em qualquer sobrevivente
    for pid in "${all_pids[@]}"; do
        kill -KILL "$pid" 2>/dev/null
    done
    wait "${all_pids[@]}" 2>/dev/null

    # ── Análise de timing estática (gráfico final de alta qualidade) ────────────
    local py="${PYTHON:-python3}"
    if [ -f "data/logs/task_timing.csv" ]; then
        echo ""
        echo "════════════════════════════════════════════════════════"
        echo "  Análise de Timing RTOS — Prova de Conformidade        "
        echo "════════════════════════════════════════════════════════"
        "$py" src/scripts/analyze_timing.py
        echo ""
        echo "Gráfico salvo em: data/logs/timing_analysis.png"
    fi

    echo ""
    echo "─── Dica: Linux de Tempo Real (PREEMPT_RT) ─────────────────"
    echo "  Para reduzir jitter de ~500µs para <50µs:"
    echo "    sudo apt install linux-image-rt-amd64 linux-headers-rt-amd64"
    echo "    sudo reboot   # selecionar kernel RT no GRUB"
    echo "  Depois execute com prioridades RT ativas:"
    echo "    sudo make run   (ou: sudo ./run.sh)"
    echo "────────────────────────────────────────────────────────────"

    exit "$exit_code"
}

trap cleanup EXIT INT TERM

# 0. Sempre roda a partir da raiz do projeto
cd "$(dirname "$0")"

if [ -z "${PYTHON:-}" ]; then
    if [ -x "./venv/bin/python" ]; then
        PYTHON="./venv/bin/python"
    else
        PYTHON="python3"
    fi
fi

# 1. Compila o núcleo C++
echo "[1/4] Compilando Núcleo RTOS C++"
mkdir -p build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release 2>&1 | tail -3
make -j"$(nproc)"
cd ..

if [ -f "./build/atr_inspection" ]; then
    EXEC_PATH="./build/atr_inspection"
elif [ -f "./bin/atr_inspection" ]; then
    EXEC_PATH="./bin/atr_inspection"
else
    echo "ERRO: executável não encontrado após compilação."
    exit 1
fi

if [ "$EUID" -eq 0 ]; then
    echo "  → root detectado: SCHED_FIFO rate-monotonic e mlockall ativos."
else
    echo "  → Sem root: SCHED_FIFO pode falhar. Use 'sudo make run' para RT real."
fi

"$EXEC_PATH" &
PID_CPP=$!
PIDS+=("$PID_CPP")

# Aguarda o núcleo C++ subir antes de abrir o monitor
sleep 2

# Monitor de timing em tempo real (não entra no array PIDS para não
# encerrar o sistema quando o usuário fechar a janela manualmente)
echo "Abrindo monitor de timing em tempo real..."
"$PYTHON" src/scripts/monitor_timing.py &
PID_MONITOR=$!

# 2. Serviços Python
echo "[2/4] Iniciando Simulador Físico"
"$PYTHON" src/scripts/tunel_simulator.py &
PIDS+=("$!")

echo "[3/4] Iniciando YOLOv8 Daemon"
"$PYTHON" src/scripts/yolo_mqtt_service.py &
PIDS+=("$!")

echo "[4/4] Iniciando GUI do Operador"
"$PYTHON" src/scripts/operator_interface.py &
PIDS+=("$!")

# Bloqueia até que qualquer componente crítico encerre (ou Ctrl+C)
wait -n "${PIDS[@]}"
