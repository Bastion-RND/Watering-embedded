import time
import usocket as socket
import uasyncio as asyncio

from micropython import const
from ubinascii import hexlify
from network import WLAN

from lib.uasync import Logger, AsyncTask, PriorityQueue, QueueEmpty, QueueFull
from lib.umqtt.packet import MQTTPacket, MQTT_VERSION_3_1_1, MQTTLastWill

from lib.umqtt.exception import MQTTException

_MQTT_LOG_LEVEL = Logger.DEBUG

_MQTT_DEFAULT_UNSECURE_PORT = const(1883)
_MQTT_DEFAULT_SECURE_PORT = const(8883)


class MQTTClient(AsyncTask):
    CONNECT_RC_ACCEPTED = const(0)
    CONNECT_RC_REFUSED = const(1)
    CONNECT_RC_ID_REJECTED = const(2)
    CONNECT_RC_SERVER_ERROR = const(3)
    CONNECT_RC_BAD_CREDENTIAL = const(4)
    CONNECT_RC_NOT_AUTHORIZED = const(5)

    SUBSCRIBE_RC_SUCCESS_QOS_0 = const(0)
    SUBSCRIBE_RC_SUCCESS_QOS_1 = const(1)
    SUBSCRIBE_RC_SUCCESS_QOS_2 = const(2)
    SUBSCRIBE_RC_FAILURE = const(0x80)

    EVENT_CONNECTED = const('connected')
    EVENT_DISCONNECTED = const('disconnected')
    EVENT_SUBSCRIBED = const('subscribed')
    EVENT_UNSUBSCRIBED = const('unsubscribed')
    EVENT_PUBLISH_SENT = const('publish_confirmed')
    EVENT_PUBLISH_RECEIVED = const('received')
    EVENT_PING_SENT = const('ping_sent')
    EVENT_PONG_RECEIVED = const('pong_received')
    EVENTS_LIST = [
        EVENT_CONNECTED,
        EVENT_DISCONNECTED,
        EVENT_SUBSCRIBED,
        EVENT_UNSUBSCRIBED,
        EVENT_PUBLISH_SENT,
        EVENT_PUBLISH_RECEIVED,
        EVENT_PING_SENT,
        EVENT_PONG_RECEIVED,
    ]

    """ OSError errno`s """
    ECONNRESET = const(104)
    ENOTCONN = const(128)

    _socket: socket.Socket | None

    _callbacks: dict[str, set[callable]] = {}

    _clean_session: bool
    _connected: bool
    _packet_id: int

    _keepalive_period: int
    _ping_ts = None

    def __init__(self, **kwargs):
        if 'name' not in kwargs.keys():
            kwargs['name'] = __class__.__name__

        AsyncTask.__init__(self, **kwargs)
        self.log.level = kwargs.get('log_level', _MQTT_LOG_LEVEL)

        self._clean_session = kwargs.get('clean_session', True)
        self._keepalive_period = kwargs.get('keepalive_period', 30)

        self._client_id = kwargs.get('client_id')

        self._username = kwargs.get('username')
        self._password = kwargs.get('password')

        self._will_message = kwargs.get(
            'will_message', MQTTLastWill(topic='status', message=b'0', retain=True, )
        )

        self._ssl = kwargs.get('ssl')
        self._ssl_params = kwargs.get('ssl_params')

        self._host = kwargs.get('host')
        self._port = kwargs.get('port') or _MQTT_DEFAULT_SECURE_PORT if self._ssl else _MQTT_DEFAULT_UNSECURE_PORT

        for event in MQTTClient.EVENTS_LIST:
            self._callbacks[event] = set()

        self._connected = False
        self._packet_id = 0

    def append_callback(self, event: str, cb: callable):
        assert event in self.EVENTS_LIST
        self._callbacks[event].add(cb)

    def remove_callback(self, event: str, cb: callable):
        assert event in self.EVENTS_LIST
        self._callbacks[event].remove(cb)

    def _emit_event(self, event: str, payload: dict = None):
        assert event in self.EVENTS_LIST
        payload = payload or dict()
        payload.update({'mqtt_client': self})
        for cb in self._callbacks[event]:
            cb(event, **payload)

    def _on_connected(self, **kwargs):
        self._connected = True
        self.log.debug(f'Connected: {kwargs}')
        self._emit_event(MQTTClient.EVENT_CONNECTED, kwargs)

    def _on_disconnected(self, **kwargs):
        if self.is_connected:
            self._connected = False
            if 'err' in kwargs.keys():
                self.log.warning(f'Connect lost: {str(kwargs.get("err"))}')
            elif 'meta' in kwargs.keys():
                self.log.warning(f'Rejected: {kwargs.get("meta")}')
            elif 'reason' in kwargs.keys():
                pass
            else:
                self.log.error(f'Disconnected: {kwargs}')

        self._socket.close()
        self._socket = None

        self._emit_event(MQTTClient.EVENT_DISCONNECTED, kwargs)

    def _on_received_msg(self, data: bytes):
        _offset = 0

        while _offset < (len(data) - 1):
            _msg = MQTTPacket(data=data[_offset:])
            _offset += len(_msg.bytes)

            if MQTTPacket.Type.PINGRESP == _msg.message_type:
                if self._keepalive_period:
                    self._ping_ts = time.ticks_ms()
                self.log.debug('Pong received')
                self._emit_event(MQTTClient.EVENT_PONG_RECEIVED)

            elif MQTTPacket.Type.PUBLISH == _msg.message_type:
                self.log.debug(f'Publish received: {_msg.meta}')
                self._emit_event(MQTTClient.EVENT_PUBLISH_RECEIVED, _msg.meta)

            elif MQTTPacket.Type.CONNACK == _msg.message_type:
                _rc = _msg.meta.get('return_code')
                if _rc == MQTTClient.CONNECT_RC_ACCEPTED:
                    self._on_connected(**_msg.meta)
                else:
                    self._on_disconnected(**_msg.meta)

            elif MQTTPacket.Type.SUBACK == _msg.message_type:
                self.log.debug(f'Subscribed: {_msg.meta}')
                self._emit_event(MQTTClient.EVENT_SUBSCRIBED, _msg.meta)

            elif MQTTPacket.Type.UNSUBACK == _msg.message_type:
                self.log.debug(f'Unsubscribed: {_msg.meta}')
                self._emit_event(MQTTClient.EVENT_UNSUBSCRIBED, _msg.meta)

            else:
                self.log.warning(f'Not implemented: {_msg}')

    def _send(self, data: bytes):
        try:
            self._socket.write(data)
            self._ping_ts = time.ticks_ms()
        except OSError as e:
            if e.errno in [MQTTClient.ECONNRESET, MQTTClient.ENOTCONN]:
                self._on_disconnected(err=e)
            else:
                self.log.error(f'OSError: {str(e)}')
        except Exception as e:
            self.log.error(f'Send error: {str(e)}')

    def _recv(self, size: int = None) -> bytes | None:
        try:
            return self._socket.read(size) if size else self._socket.read()
        except OSError as e:
            if e.errno in [MQTTClient.ECONNRESET, MQTTClient.ENOTCONN]:
                self._on_disconnected(err=e)
            else:
                self.log.error(f'OSError: {str(e)}')
        except Exception as e:
            self.log.error(f'Receive error: {str(e)}')

    @property
    def host(self) -> str | None:
        return self._host

    @property
    def port(self) -> str | None:
        return self._port

    @property
    def client_id(self) -> str:
        return self._client_id

    @property
    def packet_id(self) -> int:
        self._packet_id = 0 if self._packet_id >= 0xFFFF else (self._packet_id + 1)
        return self._packet_id

    @client_id.setter
    def client_id(self, new_client_id):
        self.disconnect()
        self._client_id = new_client_id

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def connect(self, host=None, port=None, client_id=None, **kwargs):
        self._host = host or self._host
        self._port = port or self._port

        self._client_id = client_id or self._client_id
        self._username = kwargs.get('username', self._username)
        self._password = kwargs.get('password', self._password)
        self._will_message = kwargs.get('will_message', self._will_message)
        self._clean_session = kwargs.get('clean_session', self._clean_session)
        self._keepalive_period = kwargs.get('keepalive_period', self._keepalive_period)

        self._socket = socket.socket()
        self.log.debug(f'Connecting to {self._host}:{self._port}')

        try:
            _addr = socket.getaddrinfo(self._host, self._port)[0][-1]
            self.log.debug(f'getaddrinfo: {_addr}')
        except Exception as e:
            self.log.error(f'getaddrinfo: {str(e)}')
            return

        try:
            self._socket.connect(_addr)
            self._socket.settimeout(0.001)
        except Exception as e:
            self.log.error(f'socket connect: {str(e)}')
            return

        if self._ssl is not None:
            import ussl
            self._socket = ussl.wrap_socket(
                self._socket,
                **self._ssl_params
            )

        _pkt = MQTTPacket(
            message_type=MQTTPacket.Type.CONNECT,
            protocol_version=MQTT_VERSION_3_1_1,
            clean_session=True,
            keepalive_period=self._keepalive_period,
            client_id=self.client_id,
            username=self._username,
            password=self._password,
            last_will=self._will_message,
        )
        self._send(_pkt.bytes)

        while not self.is_connected:
            await asyncio.sleep_ms(0)

    def disconnect(self):
        if self.is_connected:
            _pkt = MQTTPacket(
                message_type=MQTTPacket.Type.DISCONNECT,
            )
            self._send(_pkt.bytes)
            self._on_disconnected(reason='command')

    def subscribe(self, topic: str | tuple[str, int] | list[str | tuple[str, int]]):
        if self.is_connected:
            _pkt = MQTTPacket(
                message_type=MQTTPacket.Type.SUBSCRIBE,
                packet_id=self.packet_id,
                topic=topic,
            )
            self._send(_pkt.bytes)

    def unsubscribe(self, topic: str | tuple[str, int] | list[str | tuple[str, int]]):
        if self.is_connected:
            _pkt = MQTTPacket(
                message_type=MQTTPacket.Type.SUBSCRIBE,
                packet_id=self.packet_id,
                topic=topic,
            )
            self._send(_pkt.bytes)

    def publish(self, topic: str, payload: str | bytes = None, **kwargs):
        if self.is_connected:
            if payload is None:
                _payload = b''
            elif isinstance(payload, str):
                _payload = payload.encode()
            else:
                _payload = payload
            _pkt = MQTTPacket(
                message_type=MQTTPacket.Type.PUBLISH,
                packet_id=self.packet_id,
                topic=topic,
                payload=_payload,
                **kwargs
            )
            self._send(_pkt.bytes)

    async def _loop(self):
        if (self._socket is not None) and (_msg := self._recv()):
            self.log.trace(f'Received: {_msg}, {len(_msg)} bytes')
            self._on_received_msg(_msg)

        if self.is_connected and self._keepalive_period:
            _keepalive_ms = int((self._keepalive_period * 1000) // 10 * 9)
            if time.ticks_diff(time.ticks_ms(), self._ping_ts) >= _keepalive_ms:
                self._send(MQTTPacket(MQTTPacket.Type.PINGREQ).bytes)
                self.log.debug('Ping sent')
                self._emit_event(MQTTClient.EVENT_PING_SENT)
