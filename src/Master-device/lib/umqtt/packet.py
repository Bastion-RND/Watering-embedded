from micropython import const
from ustruct import pack, unpack
from ubinascii import hexlify

from lib.umqtt.exception import MQTTException

# @formatter:off

MQTT_VERSION_3_1            = const(3)
MQTT_VERSION_3_1_1          = const(4)

_MQTT_TYPE_UNDEFINED        = const(0)
_MQTT_TYPE_CONNECT          = const(1)
_MQTT_TYPE_CONNACK          = const(2)
_MQTT_TYPE_PUBLISH          = const(3)
_MQTT_TYPE_PUBACK           = const(4)
_MQTT_TYPE_PUBREC           = const(5)
_MQTT_TYPE_PUBREL           = const(6)
_MQTT_TYPE_PUBCOMP          = const(7)
_MQTT_TYPE_SUBSCRIBE        = const(8)
_MQTT_TYPE_SUBACK           = const(9)
_MQTT_TYPE_UNSUBSCRIBE      = const(10)
_MQTT_TYPE_UNSUBACK         = const(11)
_MQTT_TYPE_PINGREQ          = const(12)
_MQTT_TYPE_PINGRESP         = const(13)
_MQTT_TYPE_DISCONNECT       = const(14)

_MQTT_3_1_MAGIC_WORD        = const('MQIsdp')
_MQTT_3_1_1_MAGIC_WORD      = const('MQTT')

_MQTT_QOS_LEVEL_0           = const(0)  # At most once
_MQTT_QOS_LEVEL_1           = const(1)  # At least once
_MQTT_QOS_LEVEL_2           = const(2)  # Exactly once

_MQTT_CONNECT_FLAGS_LENGTH      = 1
_MQTT_CONNECT_KEEPALIVE_LENGTH  = 2

_MQTT_HEADER_RETAIN_POS     = const(0)
_MQTT_HEADER_QOS_POS        = const(1)
_MQTT_HEADER_DUP_POS        = const(3)
_MQTT_HEADER_TYPE_POS       = const(4)

# 3.1.2.3 Connect Flags
_MQTT_FLAG_CLEAN_SESSION_POS = const(1)
_MQTT_FLAG_WILL_MESSAGE_POS = const(2)
_MQTT_FLAG_WILL_QOS_POS     = const(3)
_MQTT_FLAG_WILL_RETAIN_POS  = const(5)
_MQTT_FLAG_PASSWORD_POS     = const(6)
_MQTT_FLAG_USERNAME_POS     = const(7)


# @formatter:on

def _packet_error_dump(message_type: int, data: bytes):
    result = f'Type: {message_type} [{hex(message_type)}],'
    for i in range(1, len(data)):
        result += f' {hex(data[i])}'
    return result


def _parse_length(data: bytes) -> tuple[int, int]:
    result = 0
    multiplier = 1
    bytes_count = 0
    for encoded_byte in data[:4]:
        result += (encoded_byte & 0x7f) * multiplier
        bytes_count += 1
        multiplier *= 128
        if not (encoded_byte & 0x80):
            break
    return result, bytes_count


def _parse_publish_message(data: bytes, qos: int) -> tuple[str, int | None, bytes]:
    _remaining_length, _rl_bytes_count = _parse_length(data[1:])
    assert len(data) == _rl_bytes_count + _remaining_length + 1, 'Publish len error'

    _pos = 1 + _rl_bytes_count

    _topic_len = unpack('>H', data[_pos:_pos + 2])[0]
    _pos += 2

    _topic = data[_pos: _pos + _topic_len].decode('utf8')
    _pos += _topic_len

    if qos > _MQTT_QOS_LEVEL_0:
        _packet_id = unpack('>H', data[_pos:_pos + 2])[0]
        _pos += 2
    else:
        _packet_id = None

    _payload = data[_pos:]

    return _topic, _packet_id, _payload


def _parse_data(data: bytes) -> tuple[int, dict, bytes]:
    _message_type = (data[0] & 0xF0) >> _MQTT_HEADER_TYPE_POS
    _remaining_length, _bytes_count = _parse_length(data[1:])
    _msg = data[:1 + _bytes_count + _remaining_length]
    _meta = {
        'bit': [
            data[0] & 0x01, data[0] & 0x02,
            data[0] & 0x04, data[0] & 0x08
        ]
    }

    if _MQTT_TYPE_CONNACK == _message_type:
        if _remaining_length != 2:
            raise MQTTException(f'Packet error: {_packet_error_dump(_message_type, _msg)}')
        _sp, _rc = unpack('bb', _msg[2:])
        _meta = {'session_present': _sp, 'return_code': _rc}

    elif _MQTT_TYPE_PUBLISH == _message_type:
        _qos = (_msg[0] & 0x04) << 1 | (_msg[0] & 0x02)
        _topic, _packet_id, _payload = _parse_publish_message(_msg, _qos)
        _meta.pop('bit')
        _meta.update({
            'retain': _msg[0] & 0x01,
            'dup': _msg[0] & 0x08,
            'qos': _qos,
            'topic': _topic,
            'payload': _payload,
            'packet_id': _packet_id,
        })

    elif _message_type in [_MQTT_TYPE_PUBACK, _MQTT_TYPE_PUBREC, _MQTT_TYPE_PUBREL, _MQTT_TYPE_PUBCOMP]:
        if _remaining_length != 2:
            raise MQTTException(f'Packet error: {_packet_error_dump(_message_type, _msg)}')
        _packet_id = unpack('>H', _msg[2:])[0]
        _meta = {'packet_id': _packet_id}

    elif _MQTT_TYPE_SUBACK == _message_type:
        _packet_id = unpack('>H', _msg[2:4])[0]
        _rc = [code for code in _msg[4:]]
        _meta = {'packet_id': _packet_id, 'return_codes': _rc}

    elif _MQTT_TYPE_UNSUBACK == _message_type:
        if _remaining_length != 2:
            raise MQTTException(f'Packet error: {_packet_error_dump(_message_type, _msg)}')
        _packet_id = unpack('>H', _msg[2:4])[0]
        _meta = {'packet_id': _packet_id}

    elif _MQTT_TYPE_PINGRESP == _message_type:
        if _remaining_length != 0:
            raise MQTTException(f'Packet error: {_packet_error_dump(_message_type, _msg)}')

    else:
        raise MQTTException(f'Not supported: {_packet_error_dump(_message_type, _msg)}')

    return _message_type, _meta, _msg


def _serialize_header(
        mqtt_message_type: int,
        retain=False,
        qos=_MQTT_QOS_LEVEL_0,
        dup=False
) -> bytes:
    if mqtt_message_type in [_MQTT_TYPE_SUBSCRIBE, _MQTT_TYPE_UNSUBSCRIBE]:
        qos = _MQTT_QOS_LEVEL_1
        retain = False
        dup = False
    return bytes([
        (bool(retain) << _MQTT_HEADER_RETAIN_POS) |
        (int(qos) << _MQTT_HEADER_QOS_POS) |
        (bool(dup) << _MQTT_HEADER_DUP_POS) |
        (int(mqtt_message_type) << _MQTT_HEADER_TYPE_POS)
    ])


def _serialize_length(length: int) -> bytes:
    result = b''
    while True:
        encoded_byte = length % 128
        length //= 128
        encoded_byte |= 0x80 if length else 0
        result += pack('b', encoded_byte)
        if not length:
            break
    return result


def _serialize_string(s: str) -> bytes:
    result = pack('>H', len(s))
    result += s.encode('utf8')
    return result


def _serialize_bytes(b: bytes) -> bytes:
    result = pack('>H', len(b))
    result += b
    return result


def _serialize_connect_message(**kwargs) -> bytes:
    _protocol_version = kwargs.get('protocol_version', MQTT_VERSION_3_1)
    assert MQTT_VERSION_3_1 <= _protocol_version <= MQTT_VERSION_3_1_1, 'MQTT Version error'

    _keepalive_period = kwargs.get('keepalive_period', 60)
    assert 0 <= _keepalive_period <= 65535, 'Keepalive must be in 0..65535'

    _client_id = kwargs.get('client_id')
    assert _client_id is not None and _client_id != '', 'ClientId error'

    _username = kwargs.get('username')
    _password = kwargs.get('password')
    _last_will = kwargs.get('last_will', MQTTLastWill(topic='', message=b''))

    _variable_header = _serialize_string(
        _MQTT_3_1_MAGIC_WORD if _protocol_version == MQTT_VERSION_3_1 else _MQTT_3_1_1_MAGIC_WORD
    )
    _variable_header += pack(
        'b', MQTT_VERSION_3_1 if _protocol_version == MQTT_VERSION_3_1 else MQTT_VERSION_3_1_1
    )
    _variable_header += pack(
        'b', (  # flags
                bool(kwargs.get('clean_session', False)) << _MQTT_FLAG_CLEAN_SESSION_POS |
                bool(_last_will is not None) << _MQTT_FLAG_WILL_MESSAGE_POS |
                (int(_last_will.qos) if _last_will else 0) << _MQTT_FLAG_WILL_QOS_POS |
                (bool(_last_will.retain) if _last_will else False) << _MQTT_FLAG_WILL_RETAIN_POS |
                bool(_password is not None and _username is not None) << _MQTT_FLAG_PASSWORD_POS |
                bool(_username is not None) << _MQTT_FLAG_USERNAME_POS
        )
    )
    _variable_header += pack('>H', _keepalive_period)

    _payload = _serialize_string(_client_id)
    if _last_will is not None:
        _payload += _serialize_string(_last_will.topic)
        _payload += _serialize_bytes(_last_will.message)
    if _username is not None:
        _payload += _serialize_string(_username)
    if _password is not None and _username is not None:
        _payload += _serialize_string(_password)

    _fixed_header = _serialize_header(MQTTPacket.Type.CONNECT)
    _fixed_header += _serialize_length(len(_variable_header) + len(_payload))

    return _fixed_header + _variable_header + _payload


def _serialize_publish_message(**kwargs) -> bytes:
    # print(f'-->', kwargs)
    _topic = kwargs.get('topic')
    assert _topic is not None and _topic != '', 'Topic must not be empty'

    _payload = kwargs.get('payload', b'')
    assert isinstance(_payload, bytes), 'Payload must be bytes'

    _qos = kwargs.get('qos', _MQTT_QOS_LEVEL_0)
    _packet_id = kwargs.get('packet_id', 0)

    _variable_header = _serialize_string(_topic)
    _variable_header += pack('>H', _packet_id) if _qos >= _MQTT_QOS_LEVEL_1 else b''

    _fixed_header = _serialize_header(
        MQTTPacket.Type.PUBLISH,
        retain=kwargs.get('retain', False),
        dup=kwargs.get('dup', False),
        qos=_qos,
    )
    _fixed_header += _serialize_length(len(_variable_header) + len(_payload))

    return _fixed_header + _variable_header + _payload


def _serialize_subscribe_message(**kwargs) -> bytes:
    _topics = kwargs.get('topic')
    assert _topics is not None and _topics != '' and _topics != [], 'Topic must not be empty'

    _variable_header = pack('>H', kwargs.get('packet_id', 0))
    _payload = b''

    if not isinstance(_topics, list):
        _topics = [_topics]
    for _topic in _topics:
        if isinstance(_topic, tuple):
            _qos, _str = _topic
        else:
            _qos = _MQTT_QOS_LEVEL_0
            _str = _topic

        assert _str is not None and _str != '', 'Topic must not be empty'

        _payload += _serialize_string(_str)
        _payload += pack('b', _qos)

    _fixed_header = _serialize_header(MQTTPacket.Type.SUBSCRIBE)
    _fixed_header += _serialize_length(len(_variable_header) + len(_payload))
    return _fixed_header + _variable_header + _payload


def _serialize_unsubscribe_message(**kwargs) -> bytes:
    _data = _serialize_subscribe_message(**kwargs)
    return pack('b', MQTTPacket.Type.UNSUBSCRIBE) + _data[1:]


def _serialize_pingreq_message():
    _fixed_header = _serialize_header(MQTTPacket.Type.PINGREQ)
    _fixed_header += _serialize_length(0)
    _variable_header = b''  # no variable header
    _payload = b''  # no payload
    return _fixed_header + _variable_header + _payload


def _serialize_disconnect_message():
    _fixed_header = _serialize_header(MQTTPacket.Type.DISCONNECT)
    _fixed_header += _serialize_length(0)
    _variable_header = b''  # no variable header
    _payload = b''  # no payload
    return _fixed_header + _variable_header + _payload


"""
------------------------------------------------------------------------------
"""


class MQTTLastWill:
    def __init__(self, topic: str, message: str | bytes, **kwargs):
        self._topic = str(topic)
        self._message = message if isinstance(message, bytes) else str(message).encode()
        self._qos = kwargs.get('qos', _MQTT_QOS_LEVEL_0)
        self._retain = kwargs.get('retain', False)

    @property
    def qos(self) -> int:
        return self._qos

    @property
    def retain(self) -> bool:
        return self._retain

    @property
    def topic(self) -> str:
        return self._topic

    @property
    def message(self) -> bytes:
        return self._message


class MQTTPacket:
    # @formatter:off
    class Type:
        UNDEFINED   = _MQTT_TYPE_UNDEFINED
        CONNECT     = _MQTT_TYPE_CONNECT
        CONNACK     = _MQTT_TYPE_CONNACK
        PUBLISH     = _MQTT_TYPE_PUBLISH
        PUBACK      = _MQTT_TYPE_PUBACK
        PUBREC      = _MQTT_TYPE_PUBREC
        PUBREL      = _MQTT_TYPE_PUBREL
        PUBCOMP     = _MQTT_TYPE_PUBCOMP
        SUBSCRIBE   = _MQTT_TYPE_SUBSCRIBE
        SUBACK      = _MQTT_TYPE_SUBACK
        UNSUBSCRIBE = _MQTT_TYPE_UNSUBSCRIBE
        UNSUBACK    = _MQTT_TYPE_UNSUBACK
        PINGREQ     = _MQTT_TYPE_PINGREQ
        PINGRESP    = _MQTT_TYPE_PINGRESP
        DISCONNECT  = _MQTT_TYPE_DISCONNECT
    # @formatter:on

    _message_type: int
    _data: bytes
    _meta: dict

    def __init__(self, message_type=Type.UNDEFINED, **kwargs):
        # print(f'{__class__.__name__} :ctor, type[{message_type}]', kwargs)
        if _data := kwargs.get('data'):
            self._message_type, self._meta, self._data = _parse_data(data=_data)
        else:
            self._message_type = message_type
            self._meta = kwargs

            if MQTTPacket.Type.PINGREQ == self._message_type:
                self._data = _serialize_pingreq_message()

            elif MQTTPacket.Type.PUBLISH == self._message_type:
                self._data = _serialize_publish_message(**kwargs)

            elif MQTTPacket.Type.SUBSCRIBE == self._message_type:
                self._data = _serialize_subscribe_message(**kwargs)

            elif MQTTPacket.Type.CONNECT == self._message_type:
                self._data = _serialize_connect_message(**kwargs)

            elif MQTTPacket.Type.DISCONNECT == self._message_type:
                self._data = _serialize_disconnect_message()

            else:
                raise MQTTException(f'Serializer: message type #{message_type} not supported')

    @property
    def message_type(self) -> int:
        return self._message_type

    @property
    def meta(self) -> dict[str, any]:
        return self._meta

    @property
    def bytes(self) -> bytes:
        return self._data

    @property
    def ascii(self) -> str:
        return hexlify(self._data).decode('ascii')
