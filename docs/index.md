# Sistema de Inspeção ATR

Este projeto implementa um carrinho autônomo para inspeção de túneis com uma arquitetura híbrida:

- Núcleo em C++ para tarefas concorrentes, controle e coleta de dados.
- Simulador físico em Pygame para a planta do carrinho.
- Interface do operador em Tkinter para telemetria e comandos.
- Serviço YOLOv8 para inspeção visual acionada sob demanda.

## Como executar

Antes de iniciar, certifique-se de ter um broker MQTT ativo, como Mosquitto.

```bash
pip install -r requirements.txt
make run
```

## Scripts principais

- `src/scripts/tunel_simulator.py`: simula o túnel e publica telemetria.
- `src/scripts/operator_interface.py`: exibe a GUI do operador e envia comandos.
- `src/scripts/yolo_mqtt_service.py`: processa o gatilho de câmera e publica o resultado da inspeção.

## Tópicos MQTT

- `cmd/mode`, `cmd/direction`, `cmd/speed_sp`, `cmd/camera`
- `actuator/motor`
- `sensor/lidar`, `sensor/imu`, `sensor/encoder`
- `telemetry/robot`, `telemetry/yolo`, `state/inspection`

## Documentação do código

O site da documentação é gerado com MkDocs. Para servir localmente:

```bash
mkdocs serve
```
