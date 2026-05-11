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
trabalho_atr_2026_1/
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

⚙️ Principais Funcionalidades e Requisitos Atendidos
Núcleo de Tempo Real (C++): Sistema multitarefa utilizando std::thread, com acesso concorrente protegido por std::mutex e sincronização orientada a eventos usando std::condition_variable.

Controle de Navegação: Implementação de Controlador PID clássico para manter a velocidade do robô.

Comunicação Interprocessos: Troca de dados assíncrona entre módulos isolados utilizando um Broker MQTT.

🌟 Pontos Extras Implementados:

Sensor IMU Simulado: Leitura da inclinação do túnel afetando o cálculo da gravidade no simulador físico.

Inspeção Visual por IA: Integração do modelo YOLOv8 para inferência computacional sob demanda quando uma anomalia estrutural é detectada pelo LIDAR.

🚀 Como Executar
Pré-requisitos
Certifique-se de que o seu ambiente de desenvolvimento possui os seguintes pacotes instalados:

Compilador GCC/G++ (com suporte a C++17) e make

Broker MQTT (ex: Mosquitto) rodando na máquina local (localhost:1883)

Python 3.8+ com as bibliotecas:

Bash
pip install pygame paho-mqtt ultralytics opencv-python tk
Biblioteca C++ do Paho MQTT (paho-mqtt-cpp)

Inicialização Rápida
Para facilitar a avaliação, todo o ecossistema foi encapsulado em um único arquivo de execução que compila o código e sobe todos os processos simultaneamente.

Na raiz do repositório, conceda permissão de execução (apenas na primeira vez) e execute:

Bash
chmod +x run.sh
./run.sh
Para encerrar: Basta pressionar CTRL+C no terminal ou fechar a janela da interface gráfica. O script possui um handler (trap) que cuidará de encerrar todas as instâncias em background de forma segura.
