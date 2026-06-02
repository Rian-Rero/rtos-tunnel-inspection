"""MQTT client factory and base component.

All three Python services inherit from *MqttComponent* rather than
duplicating the paho boilerplate.  Subclasses only override the two
hook methods *_on_connect* and *_on_message*.
"""

from __future__ import annotations

import logging

import paho.mqtt.client as _paho

__all__ = ["create_client", "MqttComponent"]

logger = logging.getLogger(__name__)


def create_client(client_id: str) -> _paho.Client:
    """Return a paho Client compatible with both v1 and v2 callback APIs."""
    try:
        return _paho.Client(
            client_id=client_id,
            callback_api_version=_paho.CallbackAPIVersion.VERSION1,
        )
    except TypeError:
        return _paho.Client(client_id=client_id)


class MqttComponent:
    """Base class for any Python service that speaks MQTT.

    Usage::

        class MyService(MqttComponent):
            def _on_connect(self, client):
                client.subscribe("my/topic")

            def _on_message(self, topic, payload):
                print(topic, payload)

        svc = MyService("localhost", 1883, "my-client")
        svc.connect_async()          # non-blocking (for GUI apps)
        # or
        svc.connect_blocking()       # blocks forever (for daemons)
    """

    def __init__(self, broker: str, port: int, client_id: str) -> None:
        self._broker = broker
        self._port = port
        self._client = create_client(client_id)
        self._client.on_connect = self._handle_connect
        self._client.on_message = self._handle_message

    # ── paho adapters ────────────────────────────────────────────────────────

    def _handle_connect(self, client, _userdata, _flags, rc: int) -> None:
        logger.info(
            "%s connected to %s (rc=%d)", self.__class__.__name__, self._broker, rc
        )
        self._on_connect(client)

    def _handle_message(self, _client, _userdata, msg) -> None:
        self._on_message(msg.topic, msg.payload.decode(errors="replace"))

    # ── hooks for subclasses ─────────────────────────────────────────────────

    def _on_connect(self, client: _paho.Client) -> None:
        """Called once the broker accepts the connection.  Subscribe here."""

    def _on_message(self, topic: str, payload: str) -> None:
        """Called for every inbound message after *_on_connect* subscriptions."""

    # ── public API ───────────────────────────────────────────────────────────

    def connect_async(self) -> None:
        """Connect and start the background network thread (for GUI apps)."""
        self._client.connect(self._broker, self._port, 60)
        self._client.loop_start()

    def connect_blocking(self) -> None:
        """Connect and block forever processing messages (for daemon services)."""
        self._client.connect(self._broker, self._port, 60)
        self._client.loop_forever()

    def publish(self, topic: str, payload: str | float | int) -> None:
        self._client.publish(topic, str(payload))

    def disconnect(self) -> None:
        self._client.loop_stop()
        self._client.disconnect()
