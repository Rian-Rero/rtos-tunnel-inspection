# Arquitetura

O sistema é dividido em três blocos principais:

## Núcleo C++

- Coordena threads de inspeção, navegação, coleta e reconstrução de superfície.
- Mantém o contexto compartilhado, os sinais de shutdown e os buffers concorrentes.

## Simulação e interface Python

- `tunel_simulator.py` simula a planta física e publica telemetria MQTT.
- `operator_interface.py` recebe telemetria, publica comandos e mostra o carrinho.
- `yolo_mqtt_service.py` simula a inspeção visual por demanda.

## Integração

- O operador envia comandos MQTT para o simulador.
- O simulador publica sensores e telemetria visual.
- O serviço YOLO reage ao trigger da câmera e devolve o resultado da inspeção.
