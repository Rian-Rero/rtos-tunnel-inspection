# Sistema de Inspeção ATR

Este projeto implementa um carrinho autônomo para inspeção de túneis com uma arquitetura híbrida:

- Núcleo em C++ para tarefas concorrentes, controle e coleta de dados.
- Sensores e planta simulados no núcleo C++.
- Visualizador em Pygame guiado pela telemetria MQTT.
- Interface do operador em Tkinter para telemetria e comandos.
- Serviço YOLOv8 para inspeção visual acionada sob demanda.

## Como executar

Antes de iniciar, certifique-se de ter um broker MQTT ativo, como Mosquitto.

```bash
pip install -r requirements.txt
make run
```

## Scripts principais

- `src/scripts/tunel_simulator.py`: visualiza o túnel, o carrinho e os sensores a partir da telemetria MQTT.
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
