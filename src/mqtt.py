"""Fábrica de clientes MQTT e componente base.

Os três serviços Python herdam de *MqttComponent* em vez de duplicar
o código padrão do paho. As subclasses só precisam sobrescrever os
métodos de gancho *_on_connect* e *_on_message*.
"""

from __future__ import annotations

import logging

import paho.mqtt.client as _paho

from config import MQTT_QOS

__all__ = ["create_client", "MqttComponent"]

## Registrador do módulo de infraestrutura MQTT.
logger = logging.getLogger(__name__)


def create_client(client_id: str) -> _paho.Client:
    """Retorna um cliente paho compatível com chamadas v1 e v2."""
    try:
        return _paho.Client(
            client_id=client_id,
            callback_api_version=_paho.CallbackAPIVersion.VERSION1,
        )
    except TypeError:
        return _paho.Client(client_id=client_id)


class MqttComponent:
    """Classe base para qualquer serviço Python que se comunica por MQTT.

    Uso::

        class MyService(MqttComponent):
            def _on_connect(self, client):
                client.subscribe("my/topic", qos=MQTT_QOS)

            def _on_message(self, topic, payload):
                print(topic, payload)

        svc = MyService("localhost", 1883, "my-client")
        svc.connect_async()          # não bloqueante (para GUIs)
        # ou
        svc.connect_blocking()       # bloqueia continuamente (para serviços)
    """

    def __init__(self, broker: str, port: int, client_id: str) -> None:
        """Inicializa o cliente MQTT base e registra os adaptadores de chamada."""
        ## Endereço do broker MQTT.
        self._broker = broker
        ## Porta TCP do broker MQTT.
        self._port = port
        ## Cliente paho encapsulado pelo componente.
        self._client = create_client(client_id)
        self._client.on_connect = self._handle_connect
        self._client.on_message = self._handle_message

    # ── adaptadores do paho ──────────────────────────────────────────────────

    def _handle_connect(self, client, _userdata, _flags, rc: int) -> None:
        """Adapta a chamada de conexão do paho para o gancho da subclasse."""
        logger.info(
            "%s connected to %s (rc=%d)", self.__class__.__name__, self._broker, rc
        )
        self._on_connect(client)

    def _handle_message(self, _client, _userdata, msg) -> None:
        """Decodifica a mensagem MQTT e repassa tópico e carga útil textual."""
        self._on_message(msg.topic, msg.payload.decode(errors="replace"))

    # ── ganchos para subclasses ──────────────────────────────────────────────

    def _on_connect(self, client: _paho.Client) -> None:
        """Chamado quando o broker aceita a conexão. Faça assinaturas aqui."""

    def _on_message(self, topic: str, payload: str) -> None:
        """Chamado para cada mensagem recebida após as assinaturas."""

    # ── API pública ──────────────────────────────────────────────────────────

    def connect_async(self) -> None:
        """Conecta e inicia a thread de rede em segundo plano (para GUIs)."""
        self._client.connect(self._broker, self._port, 60)
        self._client.loop_start()

    def connect_blocking(self) -> None:
        """Conecta e bloqueia continuamente processando mensagens (serviços)."""
        self._client.connect(self._broker, self._port, 60)
        self._client.loop_forever()

    def publish(self, topic: str, payload: str | float | int) -> None:
        """Publica um valor textual no tópico informado usando o QoS padrão."""
        self._client.publish(topic, str(payload), qos=MQTT_QOS)

    def disconnect(self) -> None:
        """Para a thread de rede e encerra a conexão MQTT."""
        self._client.loop_stop()
        self._client.disconnect()
