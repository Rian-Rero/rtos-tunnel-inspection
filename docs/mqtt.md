# Tópicos MQTT

## Comandos

| Tópico          | Origem | Função                      |
| --------------- | ------ | --------------------------- |
| `cmd/mode`      | GUI    | Alterna entre AUTO e MANUAL |
| `cmd/direction` | GUI    | Direção manual do carrinho  |
| `cmd/speed_sp`  | GUI    | Setpoint de velocidade      |
| `cmd/camera`    | GUI    | Trigger da inspeção visual  |

## Telemetria

| Tópico            | Origem         | Função                          |
| ----------------- | -------------- | ------------------------------- |
| `actuator/motor`  | GUI / controle | Entrada de esforço no simulador |
| `sensor/lidar`    | Simulador      | Leitura do teto                 |
| `sensor/imu`      | Simulador      | Inclinação do túnel             |
| `sensor/encoder`  | Simulador      | Estado do encoder               |
| `telemetry/robot` | Simulador      | Estado visual do carrinho       |
| `telemetry/yolo`  | YOLO           | Resultado da inspeção           |

## Fluxo

1. A GUI publica comandos.
2. O simulador atualiza a física e publica sensores.
3. O serviço YOLO responde ao trigger da câmera.
