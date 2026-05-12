# 🚇 Sistema Autônomo de Inspeção de Túneis (ATR)

![C++](https://img.shields.io/badge/C++-17-blue.svg)
![Python](https://img.shields.io/badge/Python-3.8+-yellow.svg)
![MQTT](https://img.shields.io/badge/Protocol-MQTT-red.svg)
![YOLOv8](https://img.shields.io/badge/AI-YOLOv8-brightgreen.svg)

Este repositório contém o código-fonte do sistema de controle, simulação e operação remota de um robô autônomo para inspeção de integridade estrutural em túneis. O projeto foi desenvolvido como Trabalho Final da disciplina de **Automação em Tempo Real (ATR) - 2026/1**.

O sistema utiliza uma arquitetura híbrida: um núcleo crítico de tempo real desenvolvido em **C/C++** (gerenciamento de multitarefas, sincronização e controle PID) e subsistemas periféricos em **Python** (simulação física, interface gráfica e visão computacional), totalmente integrados via protocolo **MQTT**.

## 👥 Autores

- **Rian Rero Lopes Jericó Vieira**
- **Lara Strutz Carvalho**

---

## 🏗️ Estrutura do Repositório

O projeto foi organizado utilizando os princípios de separação de responsabilidades (fatias verticais) e modularidade. Abaixo está a descrição da função de cada diretório e arquivo principal:

```text
RTOS-TUNNEL-INSPECTION/
│
├── Makefile                  # Automação da compilação do núcleo C++
├── run.sh                    # Script principal que orquestra a execução de todo o sistema
│
├── bin/                      # Contém o executável final gerado após a compilação
├── build/                    # Arquivos objeto (.o) temporários da compilação
│
├── data/                     # Armazenamento de dados em tempo de execução
│   ├── logs/                 # Registros em CSV do LIDAR e anomalias do teto
│   └── capturas/             # Imagens emuladas salvas pelo robô para análise da IA
│
├── models/                   # Modelos de Inteligência Artificial
│   └── yolov8n.pt            # Pesos pré-treinados do modelo YOLOv8 para inspeção visual
│
├── include/                  # Arquivos de cabeçalho (Headers .hpp) do C++
│   ├── core/                 # Estruturas fundamentais (Tipos de Dados, Buffers Seguros, Contexto Global)
│   └── tasks/                # Interfaces e definições das rotinas multitarefa (Threads)
│
└── src/                      # Código fonte principal
    ├── main.cpp              # Ponto de entrada do sistema C++ (instancia as threads e buffers)
    │
    ├── tasks/                # Implementação (.cpp) das threads de controle, navegação e sensores
    │
    └── scripts/              # Subsistemas e microsserviços em Python
        ├── simulador_tunel.py       # Simulação física 2D com Pygame (Física de Newton e declive)
        ├── interface_operador.py    # GUI de controle e telemetria (Tkinter)
        └── yolo_mqtt_service.py     # Daemon que processa as imagens da câmera via YOLOv8
```

## ⚙️ Principais Funcionalidades e Requisitos Atendidos

- Núcleo de Tempo Real (C++): Sistema multitarefa utilizando `std::thread`, com acesso concorrente protegido por `std::mutex` e sincronização orientada a eventos usando `std::condition_variable`.

- Controle de Navegação: Implementação de Controlador PID clássico para manter a velocidade do robô.

- Comunicação Interprocessos: Troca de dados assíncrona entre módulos isolados utilizando um Broker MQTT.

### 🌟 Pontos Extras Implementados:

- Sensor IMU Simulado: Leitura da inclinação do túnel afetando o cálculo da gravidade no simulador físico.

- Inspeção Visual por IA: Integração do modelo YOLOv8 para inferência computacional sob demanda quando uma anomalia estrutural é detectada pelo LIDAR.

---

## 🚀 Como Executar

### 1. Preparação do Ambiente

Certifique-se de que o Broker MQTT (ex: Mosquitto) está ativo no seu sistema. Instale todas as dependências do Python de uma só vez:

```bash
pip install -r requirements.txt
```

### 2. Execução Completa

Para compilar o núcleo C++ e iniciar simultaneamente o simulador, a interface do operador e o serviço de IA, utilize o comando unificado:

```bash
make run
```

Este comando garante que o código C++ está atualizado e executa o script de orquestração `run.sh`.

---

## 📚 Documentação

O projeto utiliza ferramentas de documentação automática para garantir a manutenibilidade do código.

### Gerar Documentação Unificada

Para gerar as páginas de documentação tanto do código C++ (Doxygen) quanto do código Python (MkDocs), execute:

```bash
make docs
```

- C++ (Doxygen): Disponível na pasta `html/` (abra o `index.html`).
- Python (MkDocs): Disponível na pasta `site/`.

### Visualização em Tempo Real (Python)

Para visualizar a documentação Python com suporte a live-reload enquanto desenvolve:

```bash
make docs-serve
```

---

## ⚙️ Funcionalidades Principais

- Núcleo de Tempo Real (C++): Sistema multitarefa com sincronização via `mutex` e `condition_variable`.
- Mitigação de Drift: Utilização de `sleep_until` com `steady_clock` para garantir periodicidade estrita.
- Controle de Navegação: Implementação de Controlador PID para regulação de velocidade.

### 🌟 Extras

- Sensor IMU simulado (inclinação do túnel)
- Inspeção Visual com YOLOv8 via MQTT

---

## 🛑 Encerramento

Para encerrar o sistema:

```bash
CTRL + C
```

O sistema realizará um encerramento gracioso de todos os processos ativos.
