#!/bin/bash
echo "Inicializando Sistema de Inspeção de Túneis (ATR)..."

PIDS=()
PID_CPP=""
PID_MONITOR=""

cleanup() {
    local exit_code=$?
    trap '' EXIT INT TERM

    echo ""
    echo "Encerrando sistema..."

    # SIGKILL imediato nos serviços Python e monitor (sem estado crítico para salvar)
    local kill_now=()
    [ -n "$PID_MONITOR" ] && kill_now+=("$PID_MONITOR")
    for p in "${PIDS[@]}"; do
        [ "$p" != "$PID_CPP" ] && kill_now+=("$p")
    done
    [ "${#kill_now[@]}" -gt 0 ] && kill -KILL "${kill_now[@]}" 2>/dev/null

    # Aguarda o C++ encerrar graciosamente — ele já recebeu SIGINT do terminal
    # e está fazendo join() das threads + flush do CSV de timing.
    if [ -n "$PID_CPP" ]; then
        local i
        for i in 1 2 3 4 5 6 7 8 9 10; do   # até 1 s
            kill -0 "$PID_CPP" 2>/dev/null || break
            sleep 0.1
        done
        kill -KILL "$PID_CPP" 2>/dev/null
    fi

    wait 2>/dev/null   # reap todos os zombies

    # ── Análise de timing estática (gráfico final de alta qualidade) ────────────
    local py="${PYTHON:-python3}"
    if [ -f "data/logs/task_timing.csv" ]; then
        echo ""
        echo "════════════════════════════════════════════════════════"
        echo "  Análise de Timing RTOS — Prova de Conformidade        "
        echo "════════════════════════════════════════════════════════"
        "$py" src/scripts/analyze_timing.py &
        disown $!
        echo ""
        echo "Gráfico salvo em: data/logs/timing_analysis.png"
    fi
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

# Bloqueia até Ctrl+C ou até que um componente crítico encerre.
#
# IMPORTANTE: usa `wait $!` em um sleep em background — não `wait -n`.
# `wait -n` tem um bug em bash onde o trap INT pode não disparar na
# primeira vez se um filho morre antes de o sinal ser processado.
# `wait $!` em um sleep é GARANTIDAMENTE interrompido por um único Ctrl+C.
while true; do
    sleep 1 &
    wait $!
    # Verifica se algum componente crítico encerrou por conta própria
    for pid in "${PIDS[@]}"; do
        kill -0 "$pid" 2>/dev/null || break 2
    done
done
