# Arquitetura

O sistema é dividido em três blocos principais:

## Núcleo C++

- Coordena threads de inspeção, navegação, coleta e reconstrução de superfície.
- Mantém o contexto compartilhado, os sinais de encerramento e os buffers concorrentes.

## Simulação e interface Python

- `tunel_simulator.py` visualiza o túnel e o carrinho usando apenas a telemetria MQTT do C++.
- `operator_interface.py` recebe telemetria, publica comandos e mostra o carrinho.
- `yolo_mqtt_service.py` gera uma imagem sintética da câmera embarcada e executa inferência YOLOv8 por demanda quando recebe `cmd/camera`.

## Integração

- O operador envia comandos MQTT para o núcleo C++.
- O núcleo C++ publica sensores, atuador e telemetria visual no broker.
- O serviço YOLO reage ao gatilho da câmera publicado via MQTT e devolve o resultado da inspeção em `telemetry/yolo`.
- O estado `state/inspection` é publicado pelo núcleo C++; o Python não altera esse estado diretamente.
- Não há comunicação direta entre Python e C++ fora do broker MQTT.
