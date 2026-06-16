# 🚇 Sistema Autônomo de Inspeção de Túneis (ATR)

![C++](https://img.shields.io/badge/C++-17-blue.svg)
![Python](https://img.shields.io/badge/Python-3.8+-yellow.svg)
![MQTT](https://img.shields.io/badge/Protocol-MQTT-red.svg)
![YOLOv8](https://img.shields.io/badge/AI-YOLOv8-brightgreen.svg)

Sistema de controle, simulação e operação remota de um robô autônomo para inspeção de integridade estrutural em túneis. O projeto foi desenvolvido como Trabalho Final da disciplina de **Automação em Tempo Real (ATR) - 2026/1**.

A arquitetura é híbrida: o núcleo crítico de tempo real roda em **C++17** com threads periódicas, sincronização e controle PID; os módulos periféricos rodam em **Python** para visualização, interface de operador, simulação gráfica e inspeção visual com YOLOv8. A comunicação entre processos acontece exclusivamente via **MQTT**.

## 👥 Autores

- **Rian Rero Lopes Jericó Vieira**
- **Lara Strutz Carvalho**

---

## 🏗️ Estrutura do Projeto

```text
rtos-tunnel-inspection/
├── CMakeLists.txt              # Build C++ e alvos run/part1/docs
├── run.sh                      # Orquestra o sistema completo
├── part1.sh                    # Executa apenas o núcleo C++
├── comandos.txt                # Comandos auxiliares de stress/teste RT
├── requirements.txt            # Dependências Python
├── include/
│   ├── core/                   # SharedContext, filas, logger, publisher MQTT
│   └── tasks/                  # Interfaces das tarefas C++
├── src/
│   ├── main.cpp                # Entrada do núcleo RTOS C++
│   ├── core/                   # Implementações do núcleo comum
│   ├── tasks/                  # Tarefas periódicas e ponte MQTT
│   ├── gui/                    # Interface Tkinter do operador
│   ├── simulator/              # Simulador visual em Pygame
│   ├── inspection/             # Serviço YOLOv8 via MQTT
│   └── scripts/
│       ├── operator_interface.py
│       ├── tunel_simulator.py
│       ├── yolo_mqtt_service.py
│       ├── monitor_timing.py
│       └── analyze_timing.py
├── data/
│   ├── capturas/               # Frames simulados da câmera
│   └── logs/                   # CSVs e gráficos de timing
├── models/
│   └── yolov8n.pt              # Modelo YOLOv8
├── docs/                       # Documentação MkDocs
├── html/ e latex/              # Saídas Doxygen versionadas/geradas
└── build/                      # Diretório local de build CMake
```

## ⚙️ Funcionalidades

- Núcleo C++ multitarefa com `std::thread`, `std::mutex`, `std::condition_variable` e ciclos periódicos com `sleep_until`.
- Prioridades Rate-Monotonic quando executado com permissão para escalonamento de tempo real.
- Controle PID de velocidade do robô.
- Simulação de LIDAR, IMU, encoder, atuador e reconstrução de superfície.
- Interface Tkinter para operação manual/automática e telemetria.
- Simulador Pygame guiado somente por telemetria MQTT.
- Inspeção visual com YOLOv8 por trigger MQTT.
- Monitoramento de timing em tempo real e relatório final com jitter, tempo de execução e Gantt por hiperperíodo.
- MQTT com QoS 2 (`exactly once`) em publicações e assinaturas do projeto.

---

## 🚀 Como Rodar

### 1. Dependências do sistema

No Ubuntu/Debian, instale as ferramentas principais:

```bash
sudo apt update
sudo apt install -y build-essential cmake python3 python3-pip python3-venv python3-tk mosquitto mosquitto-clients
```

Inicie o broker MQTT:

```bash
sudo systemctl enable --now mosquitto
```

Se preferir iniciar manualmente em outro terminal:

```bash
mosquitto -v
```

### 2. Ambiente Python

Na raiz do projeto:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

O `run.sh` usa automaticamente `./venv/bin/python` quando o ambiente virtual existe. Também é possível sobrescrever o interpretador com a variável `PYTHON`.

### 3. Build com CMake

O fluxo principal usado no projeto é entrar em `build/`, configurar com `cmake ..` e rodar o alvo `run`:

```bash
mkdir -p build
cd build
cmake ..
make run
```

O alvo `make run` chama `run.sh`, que:

1. recompila o núcleo C++ em modo `Release`;
2. inicia o executável `atr_inspection`;
3. abre o monitor de timing em tempo real;
4. inicia o simulador Pygame;
5. inicia o daemon YOLOv8;
6. inicia a GUI do operador.

Para ativar escalonamento RT (`SCHED_FIFO`) e `mlockall`, rode com permissão de administrador:

```bash
sudo make run
```

Sem `sudo`, o sistema ainda roda, mas o Linux pode negar as prioridades de tempo real.

### 4. Rodar apenas o núcleo C++

Para executar somente a parte C++:

```bash
cd build
cmake ..
make part1
```

Também é possível compilar diretamente:

```bash
cd build
cmake ..
make -j"$(nproc)"
./atr_inspection
```

### 5. Encerramento

Use:

```bash
CTRL + C
```

O script encerra os processos filhos, aguarda o núcleo C++ finalizar e gera a análise final de timing quando `data/logs/task_timing.csv` existir.

---

## 📊 Logs e Análise de Timing

Durante a execução, o núcleo C++ grava ciclos em:

```text
data/logs/task_timing.csv
```

Ao encerrar o sistema, o script gera:

```text
data/logs/timing_analysis.png
```

Esse gráfico contém:

- jitter de wakeup por ciclo;
- tempo de execução por tarefa;
- Gantt de um hiperperíodo central da execução, usando o MMC dos períodos das tarefas cíclicas;
- setas de deadline para as tarefas periódicas.

Também é possível gerar manualmente:

```bash
python src/scripts/analyze_timing.py data/logs/task_timing.csv
```

---

## 📡 MQTT

Todos os módulos se comunicam pelo broker MQTT local (`localhost:1883`) com QoS 2.

### Comandos

| Tópico | Origem | Função |
| --- | --- | --- |
| `cmd/mode` | GUI | Alterna entre AUTO e MANUAL |
| `cmd/direction` | GUI | Direção manual do carrinho |
| `cmd/speed_sp` | GUI | Setpoint de velocidade |
| `cmd/camera` | C++/GUI | Trigger da inspeção visual |

### Telemetria e estado

| Tópico | Origem | Função |
| --- | --- | --- |
| `actuator/motor` | C++ controle | Saída do PID |
| `sensor/lidar` | C++ LIDAR | Leitura do teto |
| `sensor/imu` | C++ IMU | Inclinação do túnel |
| `sensor/encoder` | C++ encoder | Contagem de encoder |
| `telemetry/robot` | C++ coletor | Estado visual do robô |
| `telemetry/yolo` | Python YOLO | Resultado da inspeção visual |
| `state/inspection` | C++ câmera | Estado da inspeção em andamento |

O serviço YOLO publica apenas `telemetry/yolo`. O estado `state/inspection` é controlado pelo núcleo C++ para manter GUI, simulador e câmera sincronizados.

---

## 📚 Documentação

Os alvos de documentação também ficam disponíveis pelo CMake:

```bash
cd build
cmake ..
make docs
```

Saídas principais:

- Doxygen C++: `html/index.html`
- MkDocs Python: `site/`

Para servir a documentação MkDocs com live reload:

```bash
cd build
make docs-serve
```

---

## 🧪 Testes de Carga e RT

O arquivo `comandos.txt` contém comandos auxiliares para instalar ferramentas e rodar stress/cyclictest, por exemplo:

```bash
stress-ng --cpu $(nproc) --vm 2 --vm-bytes 70% &
sudo cyclictest --mlockall --smp --priority=99 --interval=200 --distance=0 --duration=30
```

Esses comandos são úteis para avaliar jitter e comportamento sob carga, enquanto o projeto gera os logs de timing próprios em `data/logs/`.
