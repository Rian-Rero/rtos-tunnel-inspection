# Tópicos MQTT

## Comandos

| Tópico          | Origem | Função                      |
| --------------- | ------ | --------------------------- |
| `cmd/mode`      | GUI    | Alterna entre AUTO e MANUAL |
| `cmd/direction` | GUI    | Direção manual do carrinho  |
| `cmd/speed_sp`  | GUI    | Setpoint de velocidade      |
| `cmd/camera`    | C++/GUI | Trigger da inspeção visual via broker |

## Telemetria

| Tópico            | Origem         | Função                          |
| ----------------- | -------------- | ------------------------------- |
| `actuator/motor`  | C++ controle   | Saída do PID para o atuador     |
| `sensor/lidar`    | C++ LIDAR      | Leitura do teto                 |
| `sensor/imu`      | C++ IMU        | Inclinação do túnel             |
| `sensor/encoder`  | C++ encoder    | Contagem de encoder             |
| `telemetry/robot` | C++ coletor    | Estado visual do carrinho       |
| `telemetry/yolo`  | YOLO           | Resultado da inspeção           |
| `state/inspection` | C++/YOLO      | Estado da inspeção em andamento |

## Fluxo

1. A GUI publica comandos no broker MQTT.
2. O núcleo C++ consome comandos, executa as tarefas de tempo real e publica sensores, atuador e telemetria.
3. Ao detectar anomalia, o C++ publica `cmd/camera`; o serviço YOLO executa a inferência e devolve `telemetry/yolo`.
4. A GUI e o simulador Python apenas consomem os tópicos para visualização e operação.
